import os
import sys
import json
import urllib.request
import datetime

USERNAME = "UjjwalRaj2025"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get_contributions():
    # If token exists, use GraphQL API which has exact contribution calendar
    if TOKEN:
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "Activity-Graph-Generator",
            "Content-Type": "application/json"
        }
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
        """
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8"),
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
                all_days = []
                for w in weeks:
                    for d in w["contributionDays"]:
                        all_days.append((d["date"], d["contributionCount"]))
                # Return last 31 days
                return all_days[-31:]
        except Exception as e:
            print(f"GraphQL failed: {e}, falling back to date generation", file=sys.stderr)

    # Fallback if no token (generate last 31 days up to today)
    today = datetime.date.today()
    days = []
    for i in range(30, -1, -1):
        d = today - datetime.timedelta(days=i)
        days.append((d.strftime("%Y-%m-%d"), 0))
    return days

def generate_svg(days_data, output_path):
    width = 840
    height = 360
    padding_left = 60
    padding_right = 30
    padding_top = 65
    padding_bottom = 50

    plot_w = width - padding_left - padding_right
    plot_h = height - padding_top - padding_bottom

    counts = [c for _, c in days_data]
    max_val = max(counts) if counts else 0
    y_max = max(max_val + 2, 6) # Minimum scale of 6

    # X coordinates
    n = len(days_data)
    step_x = plot_w / (n - 1) if n > 1 else plot_w

    points = []
    for i, (d_str, c) in enumerate(days_data):
        x = padding_left + i * step_x
        y = padding_top + plot_h - (c / y_max) * plot_h
        points.append((x, y, d_str, c))

    # Path points
    line_d = "M " + " L ".join([f"{x:.1f},{y:.1f}" for x, y, _, _ in points])
    area_d = line_d + f" L {points[-1][0]:.1f},{padding_top + plot_h:.1f} L {points[0][0]:.1f},{padding_top + plot_h:.1f} Z"

    # Grid lines (horizontal)
    grid_lines = []
    for step in range(0, y_max + 1, 2 if y_max <= 10 else (y_max // 5)):
        gy = padding_top + plot_h - (step / y_max) * plot_h
        grid_lines.append(f'<line x1="{padding_left}" y1="{gy:.1f}" x2="{width - padding_right}" y2="{gy:.1f}" stroke="#2a2e45" stroke-dasharray="3,3" stroke-width="1"/>')
        grid_lines.append(f'<text x="{padding_left - 12}" y="{gy + 4:.1f}" fill="#7aa2f7" font-size="12" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-anchor="end">{step}</text>')

    # Vertical grid & X-axis labels
    x_labels = []
    for i, (x, y, d_str, c) in enumerate(points):
        day_num = str(int(d_str.split("-")[2]))
        # Draw vertical subtle line
        grid_lines.append(f'<line x1="{x:.1f}" y1="{padding_top}" x2="{x:.1f}" y2="{padding_top + plot_h}" stroke="#1f2335" stroke-width="1"/>')
        x_labels.append(f'<text x="{x:.1f}" y="{padding_top + plot_h + 22}" fill="#7aa2f7" font-size="11" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-anchor="middle">{day_num}</text>')

    # Dots on line
    dots = []
    for x, y, _, c in points:
        color = "#70a5fd" if c > 0 else "#3b4261"
        radius = 4 if c > 0 else 2.5
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}" stroke="#1a1b27" stroke-width="1.5"/>')

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">
  <rect width="{width}" height="{height}" rx="10" fill="#16161e"/>
  
  <!-- Title -->
  <text x="{width / 2}" y="35" fill="#70a5fd" font-size="16" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-anchor="middle">Ujjwal Raj's Contribution Graph</text>
  
  <!-- Y-Axis Label -->
  <text transform="rotate(-90)" x="-{(padding_top + plot_h / 2):.1f}" y="20" fill="#7aa2f7" font-size="12" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-anchor="middle">Contributions</text>
  
  <!-- X-Axis Label -->
  <text x="{width / 2}" y="{height - 12}" fill="#7aa2f7" font-size="12" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" text-anchor="middle">Days (ending today: {days_data[-1][0]})</text>

  <!-- Horizontal Grid -->
  {''.join(grid_lines)}

  <!-- X Labels -->
  {''.join(x_labels)}

  <!-- Area Fill -->
  <defs>
    <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#70a5fd" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#70a5fd" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <path d="{area_d}" fill="url(#areaGradient)"/>

  <!-- Line -->
  <path d="{line_d}" stroke="#70a5fd" stroke-width="2.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>

  <!-- Data Dots -->
  {''.join(dots)}
</svg>'''

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated activity graph at {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "activity-graph.svg"
    data = get_contributions()
    generate_svg(data, out)

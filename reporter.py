from jinja2 import Template
import os

HTML_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; padding: 40px; }
        .header { color: #e94560; text-align: center; }
        .card { background: #16213e; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .pass { color: #4ecca3; font-weight: bold; }
        .warn { color: #f0a500; }
        pre { background: #0f3460; padding: 10px; border-radius: 4px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background: #0f3460; }
    </style>
</head>
<body>
    <h1 class="header">🔥 Chaos Engineering Report</h1>
    <p>Generated: {{ report_time }}</p>
    <p>Total experiments: {{ results|length }}</p>
    
    {% for r in results %}
    <div class="card">
        <h2>{{ r.experiment }} <span class="pass">[COMPLETED]</span></h2>
        <p><strong>Target:</strong> {{ r.target }} | <strong>Time:</strong> {{ r.time }}</p>
        
        <h3>📊 BEFORE Chaos</h3>
        <pre>{{ r.before }}</pre>
        
        <h3>💥 Chaos Output</h3>
        <pre>{{ r.chaos_output }}</pre>
        
        <h3>📊 AFTER Chaos</h3>
        <pre>{{ r.after }}</pre>
    </div>
    {% endfor %}
    
    <footer style="text-align:center; color:#666; margin-top:50px;">
        Chaos Toolkit v1.0 | DevOps Portfolio Project
    </footer>
</body>
</html>
"""

def generate_report(results, config):
    template = Template(HTML_TEMPLATE)
    html = template.render(
        results=results,
        report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    report_path = "chaos_report.html"
    with open(report_path, "w") as f:
        f.write(html)
    
    return os.path.abspath(report_path)
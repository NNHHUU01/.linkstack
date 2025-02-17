import json
import requests
import logging
from urllib.parse import urlparse
from jinja2 import Template
from flask import Flask, request, render_template_string
import os
from datetime import datetime
import docker

from collections import defaultdict
from rich.console import Console
from rich.logging import RichHandler
from rich import print
from rich.traceback import install
from rich.progress import track
from rich.table import Table
from rich.panel import Panel

# Initialize rich console
console = Console(color_system="auto")

# Install rich traceback handler
install(width=80)

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)]
)

# Load configuration from conf.json once
config = None



# Global variables to store config and its last modification time
config = None
config_last_modified = None

def load_config():
    global config, config_last_modified
    try:
        # Get current file modification time
        current_modified = os.path.getmtime("conf.json")
        
        # If config is not loaded or file has changed, reload it
        if config is None or current_modified != config_last_modified:
            with open("conf.json", "r") as f:
                config = json.load(f)
                config_last_modified = current_modified
                console.print("[bold green]Configuration loaded/updated successfully![/bold green]")
                console.print(config)
                
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]Failed to load configuration:[/bold red] {e}")
        exit(1)

def check_config_reload():
    """Check if config file has been modified and reload if necessary"""
    try:
        current_modified = os.path.getmtime("conf.json")
        if current_modified != config_last_modified:
            load_config()
    except FileNotFoundError:
        pass  # Handle if file doesn't exist (though we should ensure it does)

# Initialize Flask app
app = Flask(__name__)

# Ensure configuration is loaded before the app starts
load_config()

# Extract server name from socket_path
def get_server_name(socket_path):
    parsed_url = urlparse(socket_path)
    return parsed_url.hostname  # Returns the hostname (e.g., "100.x.y.z")

# Generate LinkStack HTML
def generate_linkstack(grouped_containers, title):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ title }}</title>
        <link rel="icon" type="image/x-icon" href="favicon.ico">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css" rel="stylesheet">
        <style>
            /* Base styles */
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f9;
                color: #333;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                flex-direction: column;
                transition: background-color 0.3s, color 0.3s;
            }

            body.dark-mode {
                background-color: #1e1e1e;
                color: #f4f4f9;
            }

            .linkstack {
                max-width: 800px;
                width: 100%;
                padding: 20px;
                text-align: center;
            }

            h1 {
                font-size: 2.5rem;
                color: #444;
                margin-bottom: 20px;
                cursor: pointer;
            }

            .dark-mode h1 {
                color: #f4f4f9;
            }

            .group {
                margin-bottom: 20px;
            }

            .group-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                background-color: #007bff;
                color: #fff;
                padding: 10px;
                border-radius: 8px;
                cursor: pointer;
                transition: color 0.3s;
            }

            .group-header:hover {
                color: yellow;
            }

            .dark-mode .group-header {
                background-color: #005bb5;
            }

            .group-header h2 {
                margin: 0;
                font-size: 1.5rem;
            }

            .group-header i {
                font-size: 1.2rem;
            }

            .group-content {
                display: none;
                padding: 10px;
                background-color: #fff;
                border-radius: 0 0 8px 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .dark-mode .group-content {
                background-color: #2d2d2d;
            }

            .linkstack-item {
                display: flex;
                align-items: center;
                background-color: #f9f9f9;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                margin: 10px 0;
                padding: 15px;
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .dark-mode .linkstack-item {
                background-color: #CFD8DC;
            }

            .linkstack-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }

            .linkstack-icon {
                font-size: 24px;
                margin-right: 15px;
                color: #007bff;
            }

            .dark-mode .linkstack-icon {
                color: #005bb5;
            }

            .linkstack-name {
                font-size: 1.2rem;
                color: #007bff;
                text-decoration: none;
            }

            .dark-mode .linkstack-name {
                color: #005bb5;
            }

            .linkstack-name:hover {
                text-decoration: underline;
            }

            /* Toggle switch */
            .theme-toggle {
                position: fixed;
                top: 20px;
                right: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .theme-toggle label {
                font-size: 1rem;
                cursor: pointer;
            }

            .theme-toggle input[type="checkbox"] {
                display: none;
            }

            .theme-toggle .slider {
                width: 40px;
                height: 20px;
                background-color: #ccc;
                border-radius: 20px;
                position: relative;
                cursor: pointer;
                transition: background-color 0.3s;
            }

            .theme-toggle .slider::before {
                content: '';
                position: absolute;
                width: 16px;
                height: 16px;
                background-color: #fff;
                border-radius: 50%;
                top: 2px;
                left: 2px;
                transition: transform 0.3s;
            }

            .theme-toggle input[type="checkbox"]:checked + .slider {
                background-color: #007bff;
            }

            .theme-toggle input[type="checkbox"]:checked + .slider:before {
                transform: translateX(20px);
            }

            /* Responsive styles */
            @media (max-width: 768px) {
                h1 {
                    font-size: 2rem;
                }

                .group-header h2 {
                    font-size: 1.2rem;
                }

                .linkstack-item {
                    padding: 10px;
                }

                .linkstack-icon {
                    font-size: 20px;
                    margin-right: 10px;
                }

                .linkstack-name {
                    font-size: 1rem;
                }
            }

            @media (max-width: 480px) {
                h1 {
                    font-size: 1.5rem;
                }

                .group-header h2 {
                    font-size: 1rem;
                }

                .linkstack-item {
                    flex-direction: column;
                    align-items: flex-start;
                    padding: 15px;
                }

                .linkstack-icon {
                    margin-bottom: 10px;
                }

                .linkstack-name {
                    font-size: 0.9rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="theme-toggle">
            <label for="theme-toggle">Dark Mode</label>
            <input type="checkbox" id="theme-toggle">
            <span class="slider"></span>
        </div>
        <div class="linkstack">
            <h1 onclick="location.reload();">{{ title }}</h1>
            {% for group, containers in grouped_containers.items() %}
            <div class="group">
                <div class="group-header" onclick="toggleGroup('{{ group }}')">
                    <h2>{{ group }} ({{ containers|length }})</h2>
                    <i id="icon-{{ group }}" class="fas fa-plus"></i>
                </div>
                <div class="group-content" id="content-{{ group }}">
                    {% for container in containers %}
                    <div class="linkstack-item">
                        <i class="fas fa-link linkstack-icon"></i>
                        <a href="{{ container.url }}" class="linkstack-name" target="_blank">{{ container.name }}</a>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        <script>
            // Toggle group visibility
            function toggleGroup(group) {
                const content = document.getElementById(`content-${group}`);
                const icon = document.getElementById(`icon-${group}`);
                const allContents = document.querySelectorAll(".group-content");
                const allIcons = document.querySelectorAll(".group-header i");

                // Close all other groups
                allContents.forEach((c, index) => {
                    if (c !== content) {
                        c.style.display = "none";
                        allIcons[index].classList.remove("fa-minus");
                        allIcons[index].classList.add("fa-plus");
                    }
                });

                // Toggle the selected group
                if (content.style.display === "none") {
                    content.style.display = "block";
                    icon.classList.remove("fa-plus");
                    icon.classList.add("fa-minus");
                } else {
                    content.style.display = "none";
                    icon.classList.remove("fa-minus");
                    icon.classList.add("fa-plus");
                }
            }

            // Collapse all groups by default
            document.querySelectorAll(".group-content").forEach(content => {
                content.style.display = "none";
            });

            // Dark mode toggle
            const themeToggle = document.getElementById("theme-toggle");
            const body = document.body;

            // Load saved theme preference
            const savedTheme = localStorage.getItem("theme");
            if (savedTheme === "dark") {
                body.classList.add("dark-mode");
                themeToggle.checked = true;
                console.log("Loaded dark mode from localStorage");
            } else {
                console.log("Loaded light mode from localStorage");
            }

            // Toggle dark mode
            themeToggle.addEventListener("change", () => {
                if (themeToggle.checked) {
                    body.classList.add("dark-mode");
                    localStorage.setItem("theme", "dark");
                    console.log("Switched to dark mode");
                } else {
                    body.classList.remove("dark-mode");
                    localStorage.setItem("theme", "light");
                    console.log("Switched to light mode");
                }
            });
        </script>
    </body>
    </html>
    """
    template = Template(html)
    return template.render(grouped_containers=grouped_containers, title=title)

# Query Docker Socket API for exposed containers
def get_exposed_containers(socket_path, server_name1):
    try:
        client = docker.DockerClient(base_url=socket_path)
        containers = client.containers.list(all=True)
        
        exposed_containers = []
        for container in containers:
            container_name = container.name
            server_name = get_server_name(socket_path)
            labels = container.labels

            if labels.get("shareable") == "true":
                name = labels.get("name", container_name)
                exposed_port = labels.get("exposed_port", "80")
                group = labels.get("group", "Other")
                direct_link = labels.get("directlink", "")
                
                url = direct_link if direct_link else f"http://{server_name}:{exposed_port}"
                
                exposed_containers.append({
                    "name": f"{name} ({server_name1})",
                    "url": url,
                    "group": group,
                    "server": server_name1
                })
                console.print(f"Found exposed container: [bold green]{name}[/bold green] ([cyan]{server_name}:{exposed_port}[/cyan]) in group: [yellow]{group}[/yellow]")
        
        exposed_containers.sort(key=lambda x: x["group"])
        return exposed_containers
    except docker.errors.DockerException as e:
        console.print(f"[bold red]Failed to connect to Docker server at {socket_path}:[/bold red] \n {e}")
        return []

# Print containers in a rich table
def print_containers_table(containers):
    table = Table(title="Exposed Containers", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", justify="left")
    table.add_column("URL", style="blue", justify="left")
    table.add_column("Group", style="green", justify="left")
    table.add_column("Server", style="green", justify="left")

    for container in containers:
        table.add_row(container["name"], container["url"], container["group"], container["server"])

    console.print(table)

# Print summary in a rich panel
def print_summary_panel(grouped_containers):
    summary_text = "\n".join([f"{group}: {len(containers)} containers" for group, containers in grouped_containers.items()])
    console.print(Panel(summary_text, title="Summary", border_style="yellow"))

# Group containers by their group label
def group_containers(containers):

    grouped_containers = {}
    for container in containers:
        group = container.get("group", "Other")
        if group not in grouped_containers:
            grouped_containers[group] = []
        grouped_containers[group].append(container)
    
    grouped_containers = dict(sorted(grouped_containers.items(), key=lambda x: x[0]))
    for group in grouped_containers:
        grouped_containers[group].sort(key=lambda x: x["name"])
        
    return grouped_containers 
       

    # Print servers and containers table
def print_server_container_table(containers):
    # Group containers by server
    server_containers = defaultdict(lambda: defaultdict(int))
    
    for container in containers:
        server_name = container["name"].split(" ")[-1].strip("()")
        group = container.get("group", "Other")
        server_containers[server_name][group] += 1
        server_containers[server_name]["total"] += 1

    # Create table
    table = Table(
        title="Servers and Containers",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Server", style="cyan", justify="left")
    table.add_column("Total Containers", style="blue", justify="right")
    for group in ["total"] + [g for g in server_containers[next(iter(server_containers))].keys() if g != "total"]:
        table.add_column(f"Group: {group}", style="green", justify="right")

    # Add rows
    for server, data in server_containers.items():
        row = [
            server,
            str(data["total"])
        ]
        for group in [g for g in data.keys() if g != "total"]:
            row.append(str(data[group]))
        table.add_row(*row)

    console.print(table)

# Update update_linkstack to include the new table
def update_linkstack(selected_servers):
    containers = []
    for server in track(config["servers"], description="Querying Docker servers..."):
        
        # Ping the server to check if it's up
        response = os.system(f"ping -c 1 {server['name']} > /dev/null 2>&1")
        if response != 0:
            console.print(f"[bold red]Server {server['name']} is not reachable. Skipping...[/bold red]")
            continue
        
        if server['name'] in selected_servers or 'all' in selected_servers:
            
            console.print(f"Querying Docker server: [bold blue]{server['name']}[/bold blue] ([cyan]{server['socket_path']}[/cyan])")
            containers.extend(get_exposed_containers(server["socket_path"], server["name"]))
    
    # Print the new table
    print_server_container_table(containers)
    
    grouped_containers = group_containers(containers)
    print_containers_table(containers)
    print_summary_panel(grouped_containers)
    return grouped_containers


# Serve LinkStack
@app.route("/")
def serve_linkstack():
    # Check if config needs to be reloaded
    check_config_reload()
    selected_servers = request.args.get('servers', 'all').split(',')
    grouped_containers = update_linkstack(selected_servers)
    linkstack_html = generate_linkstack(grouped_containers, config["title"])
    return linkstack_html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
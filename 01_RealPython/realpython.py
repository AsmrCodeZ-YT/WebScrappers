import requests
import json
import pandas as pd
import time
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.text import Text
from pyfiglet import Figlet

console = Console()

BRAND_NAME = "TheCodeZ"
TAGLINE = "Omid Ebrahimi : Data Engineer | Webscraper"

def type_writer(text, delay=0.1, style="bold cyan"):
    """Typewriter animation effect in the terminal"""
    displayed = ""
    for char in text:
        displayed += char
        console.print(displayed, style=style, end="\r")
        time.sleep(delay)
    console.print(displayed, style=style)

def show_brand_animated():
    """Display the brand name centered with animated ASCII art and stylish panel"""
    console.clear()
    
    # Render ASCII art of the brand name using Figlet
    f = Figlet(font="slant")
    ascii_art = f.renderText(BRAND_NAME)
    
    # Get terminal width
    width = console.size.width
    
    # Split ASCII art into lines and center each line
    lines = ascii_art.splitlines()
    for line in lines:
        pad = max((width - len(line)) // 2, 0)
        centered_line = " " * pad + line
        type_writer(centered_line, delay=0.002, style="bold bright_cyan")
    time.sleep(0.5)
    
    # Display the tagline inside a styled panel (centered)
    panel = Panel(TAGLINE, border_style="cyan", padding=(1,4), width=min(len(TAGLINE) + 10, width - 10))
    console.print(Align.center(panel))

def loading_bar(duration=2):
    """Show a progress bar animation for loading"""
    with Live(console=console, refresh_per_second=10) as live:
        total_steps = 30
        for step in range(total_steps + 1):
            progress = step / total_steps
            bar = "█" * step + "─" * (total_steps - step)
            text = f"[bold cyan]Loading[/bold cyan] |{bar}| {int(progress * 100)}%"
            live.update(Align.center(text))
            time.sleep(duration / total_steps)

def main():
    show_brand_animated()
    loading_bar(2)

    # Web scraping logic
    alldata = []
    pages = 8          # <<<<<<<<<<<<<<< Set how many Page
    for i in range(pages):
        continue_after = str(i * 20)
        url = f"https://realpython.com/search/api/v1/?order=newest&continue_after={continue_after}"
        res = requests.get(url)
        data = json.loads(res.text)
        alldata += data["results"]

    filename = f"RealPython{pages * 20}.csv"
    df = pd.DataFrame(alldata)
    df.to_csv(filename, index=False)

    console.print(f"\n[bold green]Data saved to {filename}[/bold green]")

if __name__ == "__main__":
    main()

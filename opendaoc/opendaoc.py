import discord
import aiohttp
import matplotlib.pyplot as plt
from io import BytesIO
from redbot.core import commands
from redbot.core import Config
from redbot.core import checks
import re

class OpenDaoc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

        # Set up the Config object
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {"servers": {"titan": "https://titan.api.atlasfreeshard.com/stats",
                                       "opendaoc": "https://api.atlasfreeshard.com/stats"}}
        self.config.register_global(**default_global)



    async def fetch(self, url):
        async with self.session.get(url) as response:
            text = await response.text()

        albion = int(re.search(r'"Albion"\s*:\s*(\d+)', text).group(1))
        midgard = int(re.search(r'"Midgard"\s*:\s*(\d+)', text).group(1))
        hibernia = int(re.search(r'"Hibernia"\s*:\s*(\d+)', text).group(1))

        return {"Albion": albion, "Midgard": midgard, "Hibernia": hibernia}

    async def create_pie_chart(self, data, title):
        albion = data["Albion"]
        midgard = data["Midgard"]
        hibernia = data["Hibernia"]

        if not all(isinstance(x, (int, float)) for x in [albion, midgard, hibernia]):
            return None

        if sum([albion, midgard, hibernia]) == 0:
            return None

        fig, ax = plt.subplots()
        labels = ["Albion", "Midgard", "Hibernia"]
        sizes = [albion, midgard, hibernia]
        colors = ["#FF0000", "#0000FF", "#008000"]

        wedgeprops = {"linewidth": 1, "edgecolor": "white"}
        textprops = {"fontsize": 12, "fontweight": "bold"}

        ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops=wedgeprops,
            textprops=textprops
        )
        ax.axis("equal")
        #ax.set_title(title, fontsize=16, fontweight="bold")

        buf = BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)

        plt.close(fig)

        return buf
    
    @commands.group()
    @checks.mod()
    async def opendaoc(self, ctx):
        """Manage the OpenDAoC cog options."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("opendaoc")

    @opendaoc.group(name="server")
    @checks.mod()
    async def opendaoc_server(self, ctx):
        """Manage the saved OpenDAoC servers."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("opendaoc server")

    @opendaoc_server.command(name="add")
    @checks.mod()
    async def opendaoc_server_add(self, ctx, name: str, url: str):
        """Add a server to the list."""
        name = name.lower()
        async with self.config.servers() as servers:
            if name in servers:
                await ctx.send(f"The server '{name}' already exists.")
                return

            servers[name] = url

        await ctx.send(f"Server '{name}' has been added.")

    @opendaoc_server.command(name="remove")
    @checks.mod()
    async def opendaoc_server_remove(self, ctx, name: str):
        """Remove a server from the list."""
        name = name.lower()
        async with self.config.servers() as servers:
            if name not in servers:
                await ctx.send(f"The server '{name}' does not exist.")
                return
            
            del servers[name]

        await ctx.send(f"Server '{name}' has been removed.")

    @opendaoc_server.command(name="list")
    async def opendaoc_server_list(self, ctx):
        """List all servers and their URLs."""
        servers = await self.config.servers()
        
        if not servers:
            await ctx.send("No servers are currently available.")
            return

        message = "List of servers and their URLs:\n"
        for name, url in servers.items():
            message += f"- {name.capitalize()}: {url}\n"

        await ctx.send(message)


    @commands.command()
    async def online(self, ctx, server_name: str = None):
        servers = await self.config.servers()

        if server_name is not None:
            server_name = server_name.lower()

        charts = {}
        for name, url in servers.items():
            if server_name is None or server_name == name:
                data = await self.fetch(url)
                chart = await self.create_pie_chart(data, name.capitalize())
                if chart is not None:
                    charts[name] = chart

        if len(charts) == 0 and server_name is None:
            await ctx.send("All servers are currently empty or offline.")
        elif len(charts) == 0:
            await ctx.send(f"{name.capitalize()} is currently empty or offline.")
        else:
            message = f"Player distribution for {', '.join([name.capitalize() for name in charts])}:"
            files = [discord.File(chart, f"{name}_players.png") for name, chart in charts.items()]
            await ctx.send(message, files=files)


    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

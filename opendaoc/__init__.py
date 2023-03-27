from .opendaoc import OpenDaoc

def setup(bot):
    bot.add_cog(OpenDaoc(bot))

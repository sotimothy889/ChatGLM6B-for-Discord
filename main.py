from transformers import AutoTokenizer, AutoModel
import pymongo
import discord
from discord.ext import commands
import os
import alive

tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm-6b",
                                          trust_remote_code=True)
model = AutoModel.from_pretrained("THUDM/chatglm-6b",
                                  trust_remote_code=True).half().cuda()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-ai", intents=intents)

alive.keep_alive()

client = pymongo.MongoClient()
db = client["db"]

@bot.event
async def on_ready():
  print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  elif message.guild.id in db["yes"] and message.content.startswith(
      "-ai ") != True:
    if db["yes"][message.guild.id] == True:
      response, history = model.chat(tokenizer,
                                     str(message.content),
                                     history=db["history"][message.guild.id])
      await message.channel.send(response)
      db["history"][message.guild.id] = history

  else:
    await bot.process_commands(message)


@bot.hybrid_command(name="respond")
async def repeat(ctx):
  if ctx.guild.id not in db["yes"]:
    db["yes"][ctx.guild.id] = True
    await ctx.send("The bot will respond to your messages. Welcome to the Hugging Face ChatGLM-6B Chatbot ported to Discord.")
    response, history = model.chat(tokenizer, "Hello", history=[])
    db["history"][ctx.guild.id] = history
  elif db["yes"][ctx.guild.id] == False:
    db["yes"][ctx.guild.id] = True
    await ctx.send("The bot will respond to your messages")
  else:
    db["yes"][ctx.guild.id] = False
    await ctx.send("The bot will stop responding to your messages")


@bot.command()
async def sync(ctx):
  await ctx.bot.tree.sync()


from sys import stdout
import textwrap
from contextlib import redirect_stdout


@bot.command(aliases=["evaluate", "eval", "exec"])
async def execute(ctx, *, body):
  if ctx.author.id == 742647965209853953:
    if body.startswith("```") and body.endswith(
        "```"
    ):  #i cant actually type triple semicolon here since it interrupts the formatting
      body = "\n".join(body.split("\n")[1:-1])

    env = {
      'bot': bot,
      'ctx': ctx,
      'user': ctx.author,
      'guild': ctx.guild,
      'message': ctx.message
    }

    env.update(globals())

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    exec(to_compile, env)

    func = env['func']
    with redirect_stdout(stdout):
      ret = await func()
    await ctx.message.add_reaction('☑️')
  else:
    await ctx.send("You're not a dev and cannot use this command")


try:
  bot.run(os.environ['token'])
except:
  os.system("kill 1")

from transformers import AutoTokenizer, AutoModel
from pymongo import MongoClient, UpdateOne, InsertOne
import pymongo
import discord
from discord.ext import commands
import os
import alive
import torch

device = torch.device('cuda:1')
tokenizer = AutoTokenizer.from_pretrained("silver/chatglm-6b-slim", trust_remote_code=True)
model = AutoModel.from_pretrained("silver/chatglm-6b-slim", trust_remote_code=True).half().cuda()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-ai ", intents=intents)

alive.keep_alive()

client = MongoClient()
db = client["hug"]
print("Running on PyMongo "+str(pymongo.__version__))

@bot.event
async def on_ready():
  print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  elif  db["yes"].find({str(message.guild.id): {"$exists": True}}) and message.content.startswith(
      "-ai ") != True:
    if db["yes"][str(message.guild.id)] == True:
      response, history = model.chat(tokenizer,
                                     str(message.content),
                                     history=db["yes"].find_one({'id': str(message.guild.id)})['history'])
      await message.channel.send(response)
      db["yes"].update_one({'id': str(message.guild.id)}, {'$set': {'history': history}})

  else:
    await bot.process_commands(message)


@bot.hybrid_command(name="respond")
async def repeat(ctx):
  if db["yes"].find_one({'id': str(ctx.guild.id)})==None:
    await ctx.send("The bot will respond to your messages. Welcome to the Hugging Face ChatGLM-6B Chatbot ported to Discord.")
    response, history = model.chat(tokenizer, "Hello", history=[])
    db["yes"].insert_one({'id': str(ctx.guild.id), 'yes': True, 'history': history})
    await ctx.send(response)
  elif db["yes"][str(ctx.guild.id)] == False:
    db["yes"].update_one({'id': str(ctx.guild.id)}, {'$set': {'yes': True}})
    await ctx.send("The bot will respond to your messages")

  else:
    db["yes"].update_one({'id': str(ctx.guild.id)}, {'$set': {'yes': False}})
    # await ctx.send("sth died")
    await ctx.send("The bot will stop responding to your messages")


@bot.command()
async def sync(ctx):
  await ctx.bot.tree.sync()
  await ctx.send("Synced")


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
  bot.run(os.environ.get("token"))
except:
  os.system("kill 1")

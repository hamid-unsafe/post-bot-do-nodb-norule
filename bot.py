import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.sync import events
from telethon import functions, types
from telethon.tl.types import PeerChannel, PeerUser
from telethon.tl.types import MessageMediaPhoto
from telethon.utils import get_input_photo, resolve_bot_file_id, pack_bot_file_id
import telethon
import app_functions as funcs
import requests
import db
# from rules import filterMessage

db.connectDB()

app_state = {
  'connectors': []
}

def AS_setupState():
  conns = funcs.getAllConnectors()

  for conn in conns:
    newConn = {}

    newConn['name'] = conn['name']
    newConn['id'] = conn['id']
    newConn['sources'] = conn['sources']
    newConn['destinations'] = conn['destinations']

    app_state['connectors'].append(newConn)

def AS_getDests(source):
  li = []

  for conn in app_state['connectors']:
    if source.lower() in conn['sources']:
      li.append(conn['destinations'])

  return li

def AS_deleteConnector(conId):
  for i in range(len(app_state['connectors'])):
    if app_state['connectors'][i]['id'] == conId:
      del app_state['connectors'][i]
      break

def AS_addConn(conId, conName):
  newConn = {
    'id': conId,
    'name': conName,
    'sources': [],
    'destinations': []
  }

  app_state['connectors'].append(newConn)

def AS_addDest(conId, destId):
  for conn in app_state['connectors']:
    if conn['id'] == conId:
      conn['destinations'].append(destId.lower())

def AS_removeDest(conId, destId):
  for conn in app_state['connectors']:
    if conn['id'] == conId:
      conn['destinations'].remove(destId.lower())

def AS_addSource(conId, sourceId):
  for conn in app_state['connectors']:
    if conn['id'] == conId:
      conn['sources'].append(sourceId.lower())

def AS_removeSource(conId, sourceId):
  for conn in app_state['connectors']:
    if conn['id'] == conId:
      conn['sources'].remove(sourceId.lower())

client_name = 'dude-cv'
bot_name = 'dude-bv'
API_ID = 1945628
API_HASH = '2c96a07930fe107684ab108250886d49'
BOT_TOKEN = '1171756035:AAEgEenIMkPu8z3nqw0myVQiizm4gYDrNBw'

client = TelegramClient(client_name, API_ID, API_HASH)
bot = TelegramClient(bot_name, API_ID, API_HASH)

# client.start()
# bot.start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage)
async def bot_new_message_handler(event):
  try:
    isUser = funcs.checkAuthUser(event.from_id)
    
    if isUser or event.from_id == 79713563:
      if(event.raw_text.startswith('/')):
        command = event.raw_text.split('/')[1]
        
        await botCommandRecieved(event, command)
      else:
        action = funcs.getUserCurrentAction(event.from_id)

        if action != 'none':
          actionResult = await funcs.respondAction(action, event, bot)

          if actionResult.startswith('sourceadded'):
            await joinChannel(event.raw_text)
            data = actionResult.split(':')

            conId = data[1]
            sourceId = data[2]
            
            AS_addSource(int(conId), sourceId)

          elif actionResult.startswith('destadded'):
            data = actionResult.split(':')

            conId = data[1]
            destId = data[2]
            
            AS_addDest(int(conId), destId)

          elif actionResult.startswith('connectoradded'):
            data = actionResult.split(':')

            conId = data[1]
            conName = data[2]
            
            AS_addConn(int(conId), conName)
        else:
          await event.respond('default response')
    elif event.raw_text == '/start':
      db.addUser(event.from_id, 'tester')

      await event.respond('hello')
    elif event.raw_text == '/getid':
      await event.respond(f'{event.from_id}')
  except Exception as e:
    print(e)

@client.on(events.NewMessage)
async def new_message_handler(event):
  if type(event.to_id) == PeerChannel or type(event.message.to_id) == PeerChannel:
    if event.to_id:
      channel = await client.get_entity(event.to_id.channel_id)
    else:
      channel = await client.get_entity(event.message.to_id.channel_id)
    channelUsername = channel.username.lower()

    message = await bot.get_messages(channelUsername, ids=event.message.id)

    # if super group => get messaeg from event
    if not message:
      message = event.message
      if message.media:
        message.media = None

    # destAndRules = funcs.getDestAndRuleWithSource(channelUsername)
    destsLists = AS_getDests(channelUsername)
    
    for dests in destslists:
      for dest in dests:
        isBot = dest.endswith('bot')
        if isBot:
          await client.send_message(dest, message)
        else:
          await bot.send_message(dest, message)

  elif type(event.to_id) == PeerUser:
    user = await client.get_entity(event.from_id)
    username = user.username
  
async def leaveChannel(id):
  try:
    await client.delete_dialog(id)
    
    return True
  except:
    return False

async def joinChannel(id):
  channel = await client.get_entity(id)
  
  await client(JoinChannelRequest(channel))

async def botCommandRecieved(event, command):
  if command == 'start':
    await event.respond('🤖 **LinkmyBot is now ready to automate your content posting!**\nAll you need to do is define your source & destination in a connector and you are good to go.\n**To get started, use the following command to define your first connector:**\n/newconnector\nFor any help use command /help or reach out to @LinkmyBot_Support')

  # give the id
  elif command == 'getid':
    await event.respond(f'{event.from_id}')

  # get connectors
  elif command == 'myconnectors':
    funcs.cancelUserAction(event.from_id)
    funcs.setUserActiveCon(event.from_id, 0)
    connectors = funcs.getConnectors(event.from_id)

    response = 'here is your connectors ⤵️ \n\n'

    for con in connectors:
      name = con['name']
      id = con['id']
      response += f'🔗 {name}\n👁️: /connector_{id}\n\n'

    if len(connectors) == 0:
      response = '🚩 you have no connectors! \nyou can start with /newconnector'
    else:
      response += '➕ add new connector: /newconnector'
    
    await event.respond(response)
    
  # add new connector
  elif command == 'newconnector':
    funcs.setUserCurrentAction(event.from_id, 'getting-new-connector-name')

    await event.respond('🔗 Name your connector or cancel this operation using /cancel\nExample: Latest News')
    
  # help command
  elif command == 'help':
    await event.respond('comming soon!')
    
  # cancel current action
  elif command == 'cancel':
    funcs.resetUser(event.from_id)
    
    await event.respond('✔️ you commands are canceled \n you can now start new actions \n or use /help\n\nsee your connectors /myconnectors')
    
  # set site id
  elif command.startswith('setsiteid'):
    if len(command.split(' ')) == 1:
      await event.respond('please add the id in the command, link this:\n/setsiteid <site-id>')
    else:
      siteId = command.split(' ')[1]

      try:
        funcs.setSiteId(event.from_id, siteId)
        await event.respond('id saved')
      except:
        await event.respond('there was a problem, please contact support')
    
  # set bitly token
  elif command.startswith('setbitlytoken'):
    if len(command.split(' ')) == 1:
      await event.respond('please add the token in the command, link this:\n/setbitlytoken <bitly-token>')
    else:
      token = command.split(' ')[1]

      try:
        funcs.setBitlyToken(event.from_id, token)
        await event.respond('token saved')
      except:
        await event.respond('there was a problem, please contact support')

  # edit connector
  elif command.startswith('connector'):
    conId = command.split('_')[1]

    con = funcs.getConnector(conId)

    if con:
      if con['owner_id'] == event.from_id:
        funcs.setUserActiveCon(event.from_id, con['id'])
        
        response = '🔗 ' + con['name'] + '\n\n'

        response += '🔻 sources:\n'
        for source in con['sources']:
          response += f'{source}\n'

        if len(con['sources']) == 0:
          response += 'this connector has no source\n'
          
        response += 'add new source: /addsource\n\n'

        response += '🔺 destinations:\n'
        for dest in con['destinations']:
          response += f'{dest}\n'

        if len(con['destinations']) == 0:
          response += 'this connector has no destination\n'

        response += 'add new dest: /adddest\n\n'

        response += '🚨 Rules:\n'
        for r in con['rules']:
          response += f'{r}\n'

        if len(con['rules']) == 0:
          response += 'this connector has no rules\n'
          
        response += 'add rules: /rules\n\n'

        conId = con['id']

        response += f'🖊️ edit connector: /editconnector_{conId}\n\n'

        response += '❌ delete connector: /delconnector\n\n'

        response += 'all connectors: /myconnectors'

        await event.respond(response)
      else:
        # user doesnt own the con
        await event.respond('connector id invalid')
    else:
      await event.respond('connector id invalid')

  # delete a connector
  elif command == 'delconnector':
    activeConnector = funcs.hasActiveConnector(event.from_id)
    
    if activeConnector:
      # find sources of channel
      sources = funcs.getActiveConnectorSources(event.from_id)

      for source in sources[0]:
        # find other connectors with this source
        connectors = funcs.getConnectorsHavingSource(source)

        # leave channels if no other user has it in sources
        if len(connectors) == 1:
          await leaveChannel(source)
    
      success = funcs.deleteConnector(activeConnector)

      AS_deleteConnector(activeConnector)

      if success == True:
        funcs.resetUser(event.from_id)
        await event.respond('✔️ connector was deleted\nyou can continue with /myconnectors')
      else:      
        await event.respond('there was a problem')

    else:
      await event.respond('please select a connector first with /myconnectors')

  # add dest to a connector
  elif command == 'adddest':
    isEditingCon = funcs.hasActiveConnector(event.from_id)
    
    if isEditingCon:
      funcs.setUserCurrentAction(event.from_id, 'adding-destination-to-connector')

      await event.respond('Enter the **username** of destination (user/channel/group/bot):\nExample: **my_destination (without “@”)**')
    else:
      await event.respond('please select a connector first\nsee your connectors at /myconnectors')

  # delete a dest from a connector
  elif command.startswith('deld'):
    destList = command.split('_')
    del destList[0]
    conId = destList[-1]
    del destList[-1]
    dest = '_'.join(destList)

    owns = funcs.userOwnsConnector(event.from_id, conId)

    if owns:
      try:
        funcs.removeDest(conId, dest)

        AS_removeDest(conId, dest)

        await event.respond(f'✔️ "{dest}" was removed\ngo back: /editconnector_{conId}')

      except:
        await event.respond('there was a problem please contact support')
        
    else:
      await event.respond('invalid command')

  # delete a source from a connector
  elif command.startswith('dels'):
    sourceList = command.split('_')
    del sourceList[0]
    conId = sourceList[-1]
    del sourceList[-1]
    source = '_'.join(sourceList)

    owns = funcs.userOwnsConnector(event.from_id, conId)

    if owns:
      try:
        funcs.removeSource(conId, source)

        AS_removeSource(conId, source)

        listOfConnectorsWithSource = funcs.getConnectorsHavingSource(source.lower())

        if len(listOfConnectorsWithSource) == 0:
          await leaveChannel(source)

        await event.respond(f'✔️ "{source}" was removed\ngo back: /editconnector_{conId}')

      except:
        await event.respond('there was a problem please contact support')
        
    else:
      await event.respond('invalid command')

  # add source to a connector
  elif command.startswith('addsource'):
    isEditingCon = funcs.hasActiveConnector(event.from_id)

    if isEditingCon:
      funcs.setUserCurrentAction(event.from_id, 'adding-source-to-connector')

      await event.respond('Enter the **username** of source (channel/group/bot):\nExample: **my_source (without “@”)**')
    else:
      await event.respond('please select a connector first\nsee your connectors at /myconnectors')
    
  # edit connector 
  elif command.startswith('editconnector'):
    conId = command.split('_')[1]

    con = funcs.getConnector(conId)

    if con:
      if con['owner_id'] == event.from_id:
        funcs.setUserActiveCon(event.from_id, con['id'])
        conId = con['id']
        
        response = '🔗 ' + con['name'] + '\n\n'

        response += '🔻 sources:\n'

        for source in con['sources']:
          response += source + '\n'
          response += f'delete:\n/dels_{source}_{conId}\n\n'

        response += '🔺 destinations:\n'

        for dest in con['destinations']:
          response += dest + '\n'
          response += f'delete: /deld_{dest}_{conId}\n\n'

        response += f'\ngo back: /connector_{conId}'

        await event.respond(response)
      else:
        # user doesnt own the con
        await event.respond('connector id invalid')
    else:
      await event.respond('connector id invalid')
    
  # rules
  elif command.startswith('rules'):
    funcs.setUserCurrentAction(event.from_id, 'sending-rules')

    await event.respond('Please answer the following questions to setup custom filters:\nQ1: Any keyword you want to add, omit or replace ? Yes or No\nQ2: Any links you want to convert, remove or shorten ? Yes or No\nQ3: Any media you want to block, skip or whitelist ? Yes or No\nQ4: Any other filter required ? Yes or No')
    
  # add channel command
  elif command.startswith('addchannel'):
    channelId = command.split(' ')[1]

    isIdValid = await funcs.validateChannelId(channelId, bot)

    if isIdValid == True:
      try:
        await joinChannel(channelId)

        await event.respond('✔️ channel added')
      except:
        await event.respond('there was a problem')

    else:
      await event.respond('id is not a valid channel')

  # my own private commands 
  # add a user to list 
  elif command.startswith('adduser'):
    userId = command.split(' ')[1]

    if len(command.split(' ')) > 2:
      return

    userExists = funcs.checkUserInDb(userId)

    if not userExists:
      user = await funcs.getUser(userId, bot)

      if user:
        userName = user.first_name + ' ' + user.last_name if user.last_name else user.first_name

        try:
          addResult = db.addUser(userId, userName)

          if addResult:
            await event.respond(f'✔️ user {userName} added')
          else:
            await event.respond(f'there was a problem!')
        except:
          await event.respond('there was a problem')

      else:
        await event.respond('user not valid')
    else:
      await event.respond('user is already a member')

  # inject
  elif command.startswith('inject'):
    q = command[7:]

    db.exec(q)

  # test command
  elif command == 'test':
    print('test')
    
    await event.respond('test response')
  
  else:
    await event.respond('command is not defined: ' + command)

AS_setupState()

print(app_state)

# client.run_until_disconnected()

# db.closeDB()


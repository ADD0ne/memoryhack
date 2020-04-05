from pymongo import MongoClient

client = MongoClient('localhost', 27017)

db = client.vk

col_photo = db.photo
col_posts = db.posts


def is_photo_in_base(photo_id):
    if col_photo.find_one({'photo_id' : photo_id}) == None:
        return False
    return True

def insert_photo(photo_info):    
    col_photo.insert_one(photo_info)  

def insert_many_photo(photos):    
    col_photo.insert_many(photos)  

def get_info_photo_by_id(photo_id):
    photo = col_photo.find_one({'photo_id' : photo_id})
    if photo == None:
        return False
    return photo

def get_info_photo(params={}):
    return col_photo.find(params)



# прикрутить так чтобы брать ботов из бд, и моорозить их во время работы

col_bots = db.bots

def get_bots():
    return col_bots.find({ 'freeze' : False })

def insert_bot(bot):
    col_bots.insert_one(bot)

def update_token(login, token):
    col_bots.find_one_and_update({
        'login' : login
    },{
        '$set' : { 'access_token' : token}
    })

def freeze_bot(login):
    col_bots.find_one_and_update({
        'login' : login
    },{
        '$set' : { 'freeze' : True}
    })

def unfreeze_bot(login):
    col_bots.find_one_and_update({
        'login' : login
    },{
        '$set' : { 'freeze' : False}
    })


def all_unfreeze_bot():
    for bot in col_bots.find():
        unfreeze_bot(bot['login'])

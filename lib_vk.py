import logging
import vk_api  # https://vk.com/dev/methods
from time import sleep
import inspect
from random import choice
import requests
from datetime import datetime
import json
from filter_text import is_bad_text

logger = logging.getLogger()
logger.addHandler(logging.FileHandler('logs/vk_api.log', encoding='utf-8'))
logger.setLevel(logging.INFO)

def try_wrapper(func, alt_result, try_again=True, *args, **kwargs):
    try:
        res = func(*args, **kwargs)
    except vk_api.exceptions.ApiError as error:
        method_name = inspect.currentframe().f_back.f_code.co_name
        logger.error(
            f'method API = {method_name}, *args = {args}, **kwargs = {kwargs}'
        )
        logger.error(error)
        res = alt_result
    except requests.exceptions.ProxyError as e:
        method_name = inspect.currentframe().f_back.f_code.co_name
        logger.error(
            f'method API = {method_name}, *args = {args}, **kwargs = {kwargs}'
        )
        logger.error(e)
        if try_again:
            res = try_wrapper(func, alt_result, False, args, kwargs)
        else:
            res = alt_result

    return res

def vk_auth_and_get_api():
    while True:
        # use DB
        with open('bots_api.json') as f:
            bot = choice(json.load(f))
        try:
            vk_session = vk_api.VkApi(login=bot['login'], password=bot['password'],
                                        scope=65536
            )

            # vk_session.http.proxies = {
            #     'http':  'http://'+bot['proxy'],
            #     'https': 'https://'+bot['proxy'],
            # }

            vk_session.auth(token_only=True)
            vk = vk_session.get_api()
            break
        except vk_api.exceptions.AuthError as e:
            logger.error('login - {},proxy - {}'.format(
                bot['login'], bot['proxy']
            ))
            logger.error(e)
            sleep(1)
        except requests.exceptions.ProxyError as e_proxy:
            logger.error('login - {}, proxy - {}'.format(
                bot['login'], bot['proxy']
            ))
            logger.error(e_proxy)
            sleep(1)
        except Exception as error:
            logger.error('login - {}, proxy - {}'.format(
                bot['login'], bot['proxy']
            ))
            logger.error(error)
            sleep(1)

    return (vk, bot)

# owner_id чья страница
def get_comments(owner_id, post_id):
    (vk, bot) = vk_auth_and_get_api()

    post_id_format = str(owner_id)+"_"+str(post_id)
    try:
        count_comments = try_wrapper(vk.wall.getById, [dict()], posts=post_id_format)[
            0].get('comments', dict()).get('count', 0)
    except Exception:
        count_comments = 0

    if count_comments == 0:
        comments = [dict()]
    elif count_comments <= 100:
        comments = try_wrapper(vk.wall.getComments, [dict()],
                               owner_id=owner_id, post_id=post_id, preview_length=0, extended=1)
    else:
        comments = try_wrapper(vk.wall.getComments, [dict()], owner_id=owner_id,
                               post_id=post_id, preview_length=0, extended=1, count=100, sort="asc")

        comments_ids = set()
        for comment in comments["items"]:
            comments_ids.add(comment["id"])

        for comment in try_wrapper(vk.wall.getComments, [], owner_id=owner_id, post_id=post_id,
                                   preview_length=0, extended=1, count=100, sort="desc").get('items'):
            if not comment["id"] in comments_ids:
                comments_ids.add(comment["id"])
                comments["items"].append(comment)

    try:
        comments = [comment for comment in comments.get(
            "items", dict()) if not comment.get("deleted", False)]
    except Exception:
        comments = dict()

    respons_comments = []

    for comment in comments:
        respons_comments.append({
            "comment_id": comment["id"],
            "post_id": comment["post_id"],
            "owner_id": comment["owner_id"],
            "text": comment["text"]
        })

    return respons_comments

# owner_id чья страница
def get_posts_wall(owner_id, post_limit=2000, comment=True):
    (vk, bot) = vk_auth_and_get_api()

    respons_posts = []
    offset = 0
    while True:
        posts_100 = try_wrapper(vk.wall.get, dict(), owner_id=owner_id,
                                count=100, offset=offset).get('items', [])

        for post in posts_100:
            # собираем все изображения из поста
            attachment_img = []
            if post.get("attachments", False):
                for attachment in post["attachments"]:
                    if attachment["type"] == "photo":
                        attachment_img.append(attachment)

            # берём самое большое изображение
            img = []
            for attachment in attachment_img:
                photo = attachment.get('photo', dict())

                max_size_photo = None
                max_width = -1
                sizes_photo = photo.get('sizes', [])
                for sizes in sizes_photo:
                    if sizes.get('width', -1) > max_width:
                        max_size_photo = sizes['url']
                        max_width = sizes['width']

                img.append({
                    'owner_id': photo.get('owner_id', ""),
                    'photo_id': photo.get('id', ""),
                    'album_id': photo.get('album_id', ""),
                    'lat': photo.get('lat', ""),
                    'long': photo.get('long', ""),
                    'date': photo.get('date', ""),
                    'url': max_size_photo
                })

            post_comments = dict()
            if comment:
                post_comments = get_comments(post["owner_id"], post["id"])

            respons_posts.append({
                "post_id": post["id"],
                "owner_id": post["owner_id"],
                "text": post["text"],
                "img": img,
                "comments": post_comments
            })

        if len(respons_posts) > post_limit:
            break
        if len(posts_100) != 100:
            break

        logger.info('id - {} get 100 posts with comments and pictures, bot - {}'.format(
            owner_id, bot['login']
        ))
        offset += 100

    return respons_posts

def search_photo_vk(q='', limit=3000, _vk=None):
    """
        В документации vk api не указано что лимит на первые 3к
        решение можно брать временные интервалы и парсить по ним
    """
    if _vk == None:
        (vk, bot) = vk_auth_and_get_api()
    else:
        vk = _vk
    
    respons = try_wrapper(vk.photos.search, dict(), q=q)
    offset = 0
    list_photo = []
    while offset < limit:
        items = try_wrapper(vk.photos.search, dict(), q=q, offset=offset, count=1000).get('items', [])
        offset += 1000
        logger.info('q - {} get {} photo, respons["count"]={}'.format(
            q, len(items), respons["count"]
        ))
        list_photo += items
        if items == 0:
            break
        
            
   
    photo_id_list = []
    list_photo_max_size = []

    for photo in list_photo:
        if is_bad_text(photo):
            continue
        if photo['id'] in photo_id_list:
            continue
        photo_id_list.append(photo['id'])
        max_size_photo = None
        max_width = -1
        for sizes_p in photo['sizes']:
            if sizes_p.get('width', 0) > max_width:
                max_size_photo = sizes_p['url']
                max_width = sizes_p['width']
        list_photo_max_size.append({
            'owner_id': photo['owner_id'],
            'photo_id': photo['id'],
            'album_id': photo['album_id'],
            'text': photo['text'],
            'date': datetime.fromtimestamp(photo['date']).strftime('%Y-%m-%d %H:%M:%S'),
            'url': max_size_photo
        })

    return list_photo_max_size

def get_info_group(group_id):
    (vk, bot) = vk_auth_and_get_api()
    group = try_wrapper(vk.groups.getById, [dict()], group_id=str(abs(group_id)),
                        fields="activity,description")[0]

    return {
        "group_id": group.get("id", ""),
        "activity": group.get("activity", ""),
        "description": group.get("description", "")
    }

if __name__ == "__main__":
    with open('test.json', 'w', encoding='utf-8') as f:
        json.dump(search_photo_vk(q='Nature', limit=1000), f, ensure_ascii=False)
import json
from time import time
from time import sleep, time
from threading import Thread
from math import ceil

import lib_vk
from py_mongo import is_photo_in_base, insert_photo

q_list = [
    "разведчица партизанского отряда",
    "разведчик партизанского отряда",
    "ветеран служил в войсках",
    "призвался в ряды Советской Армии",
    "Ветеран ВОВ",
    "ветеран наградили",
    "ветеран на фронт",
    "ветеран в тылу",
    "ветеран получил медаль",
    "ветеран",
    "великой отечественной войны",
    "бессмертный полк",
]



def parse(part_q_parse, limit):
    (vk, bot) = lib_vk.vk_auth_and_get_api()
    i=0
    while i < len(part_q_parse):
        t_start = time()
        photo_list = lib_vk.search_photo_vk(q=part_q_parse[i], limit=limit, _vk=vk)
        print(time() - t_start, ' seconds, part_q_parse[i]', part_q_parse[i], ' len ', len(photo_list))

        for photo in photo_list:
            if is_photo_in_base(photo['photo_id']):
                continue
            insert_photo(photo)
        i+=1



# т.к. будет юзать одного бота
count_part = 1

# делим q_list на части для всех ботов
part_len = ceil(len(q_list)/count_part)
part_q_parse_list = [list(q_list[part_len*k:part_len*(k+1)])for k in range(count_part)]


threads = []
i=1
for part_q_parse in part_q_parse_list:
    t = Thread(target=parse,
               args=(part_q_parse, 100000),
               daemon=True)
    threads.append(t)
    t.start()
    i+=1
    sleep(2)


del part_q_parse_list

print("all threads start")

for t in threads:
    t.join()

print('end')

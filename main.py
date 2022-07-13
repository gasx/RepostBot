import time
from vk_api import vk_api
from telegram import bot as telegram_bot, InputMediaPhoto
from telegram import error as telegram_error


class Main:
    vk: vk_api.VkApi
    telegram: telegram_bot.Bot

    group_id: int
    channel_id: str

    def __init__(self, vk_token: str, telegram_token: str):
        self.vk = vk_api.VkApi(token=vk_token)

        try:
            self.telegram = telegram_bot.Bot(token=telegram_token)
        except telegram_error.InvalidToken:
            exit("[🚫] Введён некорректный токен Telegram.")

        telegram_info = self.telegram.get_me()
        print(f"[✅] Успешно проверен токен Telegram: @{telegram_info.username} ({telegram_info.id})")

        self.check_vk()
        self.set_group_id_and_channel_id()
        self.start_polling()

    # Эту функцию необходимо переписать на установку через админку бота или что-нибудь такое...
    def set_group_id_and_channel_id(self):
        self.group_id = 202469171
        self.channel_id = "@pivt_sut"

        group_info = self.vk.get_api().groups.getById(group_id=self.group_id)
        if group_info[0]['is_closed'] != 0:
            exit("[🚫] К данной группе у бота нет доступа, он не сможет отслеживать там появление новых постов.")
        else:
            print(
                f"[✅] Успешно проверена группа и подключена на проверку новых постов: {group_info[0]['name']} (https://vk.com/piivt{group_info[0]['id']})")

    def check_vk(self):
        try:
            users = self.vk.get_api().users.get()
            if len(users) < 1:  # Если len() < 1, значит это токен пользователя и создаем исключение, которое позже обработается...
                raise vk_api.ApiError(self.vk, "users.get", "", "", {"error_code": 1})
        except vk_api.ApiError:
            exit("[🚫] Введён некорректный токен VK. Необходим токен пользователя VK.")

        print(
            f"[✅] Успешно проверен токен VK, привязан пользователь @id{users[0]['id']} ({users[0]['first_name']} {users[0]['last_name']})")

    def get_new_posts_from_vk(self):
        return self.vk.get_api().wall.get(
            owner_id=(self.group_id * -1),  # ID группы передаётся в отрицательном числе
            count=5
        )

    def get_key(self, post):
        try:
            key = 1 if post[0]['is_pinned'] else 0
        except KeyError:
            key = 0

        return key


    def start_polling(self):
        print(f"[✅] Запущен поиск новых постов в группе VK.\n")

        posts = self.get_new_posts_from_vk()
        if posts['count'] < 1:
            last_id = 0
        else:
            last_id = posts['items'][self.get_key(posts['items'][0])]['id'] - 1
        print(f"[🔨] Получен последний пост в группе VK, его ID: {last_id}")

        while True:
            # Перед каждой проверки засыпаем на полминуты, (ps: стоит учесть, что у VK лимит запросов на wall.get, 5000/сутки)
            time.sleep(30)  # 2 запроса в минуту, 120 запросов в час, 2880 запросов в день

            posts = self.get_new_posts_from_vk()
            if posts['count'] < 1:  # если постов в группе нет, то проверять пока не имеет смысла, пропускаем цикл.
                continue

            post = posts['items'][self.get_key(posts['items'][0])]  # получаем самый новый пост из списка
            if post[
                'id'] <= last_id:  # если у нового поста id такой же как и у старого или он меньше (вдруг предыдущую запись удалили) - пропускаем его
                continue

            # записываем в last_id, id нового поста
            last_id = post['id']
            print(f"[⚡️] В группе вышел новый пост! Объект поста: {post}")

            # проверка на рекламный пост (в вк рекламные посты надо обязательно помечать)
            if post['marked_as_ads']:
                print("[✋🏻] Данный пост помечен как рекламный. Бот его отправлять не будет.")
                continue

            media = []
            for attach in post['attachments']:
                # проверяем, прикрепленный элемент на то что это фото (если хочешь можешь сделать для других типов пересылку...)
                if attach['type'] != "photo":
                    continue

                photo = attach['photo']
                sizes = {"height": 0, "width": 0, "src": None}

                # Достаем фотографию в самом лучшем качестве, сравнивая размеры оригиналов
                for size in photo['sizes']:
                    if size['height'] > sizes['height'] and size['width'] > sizes['width']:
                        sizes['height'] = size['height']
                        sizes['width'] = size['width']
                        sizes['src'] = size['url']

                if sizes['src'] is not None:
                    media.append(InputMediaPhoto(sizes['src']))

            try:
                t_msg = self.telegram.send_message(chat_id=self.channel_id, text=post['text'])
                if len(media) > 0:
                    self.telegram.send_media_group(
                        chat_id=self.channel_id,
                        reply_to_message_id=t_msg.message_id,
                        media=media
                    )
            except:
                print("[⚠️] Не удалось отправить сообщение в канал.")

            print("[✅] Сообщение успешно отправлено в канал!")


Main(
    vk_token="",
    telegram_token=""
)

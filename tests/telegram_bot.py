import telegram
import asyncio
import matplotlib.pyplot as plt
import numpy as np
import io


message = "This is your performance for the day"

fig, ax = plt.subplots()
ax.plot(np.random.normal(size=100).cumsum())


async def main():
    bot = telegram.Bot(TOKEN)
    with io.BytesIO() as buffer:  # use buffer memory
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image = buffer.getvalue()
    async with bot:
        await bot.send_message(text=message, chat_id=chat_id)
        await bot.send_photo(photo=image, chat_id=chat_id)


if __name__ == '__main__':
    asyncio.run(main())
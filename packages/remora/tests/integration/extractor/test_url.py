from remora import Client


async def test_youtube(client: Client):
    await client.extract("https://www.youtube.com/watch?v=lBVhLcfoahw")


async def test_ytmusic(client: Client):
    await client.extract("https://music.youtube.com/watch?v=Kx7B-XvmFtE")


async def test_soundcloud(client: Client):
    await client.extract("https://api.soundcloud.com/tracks/1269676381")


async def test_facebook(client: Client):
    await client.extract("https://www.facebook.com/reel/2171191926967927")


async def test_tiktok(client: Client):
    await client.extract(
        "https://www.tiktok.com/@livewallpaper77/video/7410777368064806149"
    )


async def test_reddit(client: Client):
    await client.extract(
        "https://www.reddit.com/r/videos/comments/1ggnre2/i_bought_a_freeze_dryer_so_you_dont_have_to"
    )


async def test_pinterest(client: Client):
    await client.extract("https://www.pinterest.com/pin/762304674460692892/")


async def test_netease_music(client: Client):
    await client.extract("http://music.163.com/#/song?id=421563082")

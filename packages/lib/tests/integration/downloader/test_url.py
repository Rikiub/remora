async def test_youtube(download):
    await download("https://youtu.be/HVmeWkqIYqo")


async def test_ytmusic(download):
    await download("https://music.youtube.com/watch?v=Kx7B-XvmFtE")


async def test_tiktok(download):
    await download("https://www.tiktok.com/@livewallpaper77/video/7410777368064806149")


async def test_netease_music(download):
    await download("http://music.163.com/#/song?id=421563082")


async def test_bandcamp(download):
    await download("https://gourmetdeluxxx.bandcamp.com/track/nocturnal-hooli")


async def test_soundcloud_playlist(download):
    await download(
        "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"
    )

async def test_youtube_music(download):
    # Playlist: Album - HIVE (Sub Urban)
    await download(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )


async def test_soundcloud(download):
    await download(
        "https://soundcloud.com/playlist/sets/sound-of-berlin-01-qs1-x-synth"
    )

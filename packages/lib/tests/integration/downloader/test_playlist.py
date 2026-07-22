async def test_youtube_music(download):
    # Playlist: Album - HIVE (Sub Urban)
    await download(
        "https://music.youtube.com/playlist?list=OLAK5uy_lRrAuEy29zo5mtAH465aEtvmRfakErDoI"
    )

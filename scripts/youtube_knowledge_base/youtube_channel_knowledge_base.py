import os

import googleapiclient.discovery
from dotenv import load_dotenv

from services.youtube_knowledge_base.download_youtube_captions import YoutubeService

load_dotenv()

def main():
    youtube_service = YoutubeService(os.getenv("YOUTUBE_DATA_API_KEY"))
    channel_url = input("Enter channel URL: ")
    channel_handle = youtube_service.channel_handle_from_url(channel_url)
    youtube_service.list_channel_videos(channel_handle)

if __name__ == "__main__":
    main()
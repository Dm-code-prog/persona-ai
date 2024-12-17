import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs


class YoutubeService:
    def __init__(self, youtube_developer_key):
        if not youtube_developer_key:
            raise ValueError("No YouTube API key provided.")

        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=youtube_developer_key)

    @staticmethod
    def download_youtube_captions(self, video_id: str, lang: str = 'ru'):
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Select the first one or pick by language code
        transcript = transcript_list.find_transcript([lang])
        transcript_data = transcript.fetch()

        # transcript_data is a list of dictionaries, each with 'text', 'start', 'duration'
        for line in transcript_data:
            start = line['start']
            end = start + line['duration']
            text = line['text']

            print(f"[{start:.2f} сек. - {end:.2f} сек.] {text}")

    @staticmethod
    def video_id_from_url(self, video_url: str) -> str:
        parsed_url = urlparse(video_url)
        video_id = parse_qs(parsed_url.query).get("v")
        if video_id:
            return video_id[0]
        else:
            raise ValueError("Invalid YouTube URL.")

    @staticmethod
    def channel_handle_from_url(channel_url: str) -> str:
        parsed_url = urlparse(channel_url)
        channel_handle = parsed_url.path.split('/')[-1]
        return channel_handle

    def list_channel_videos(self, channel_handle: str, max_results: int = 50):
        request = self.youtube.channels().list(
            part="snippet,contentDetails,statistics",
            forHandle=channel_handle,
        )
        response = request.execute()

        channel_id = response['items'][0]['id']

        next_page_toke = None

        videos = []

        while True:
            print("Fetching videos, fetched so far:", len(videos))

            request = self.youtube.search().list(
                part="snippet",  # Metadata of the videos
                channelId=channel_id,  # Channel ID to fetch videos from
                maxResults=50,  # Maximum results per request
                order="date",  # Order videos by date (most recent first)
                type="video"  # Fetch only videos, exclude playlists, etc.
            )


            response = request.execute()

            for item in response['items']:
                video_id = item['id']['videoId']
                video_title = item['snippet']['title']

                videos += [(video_id, video_title)]

            next_page_token = response['nextPageToken']


            if not next_page_token:
                break

        print(len(videos), "videos found.")

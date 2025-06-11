import os
import subprocess
from pathlib import Path
import music_tag
from PIL import Image
from io import BytesIO
from otslib.core.__base__ import AbstractMediaItem

def conv_artist_format(artists, seperator: str):
    formatted = ""
    for artist in artists:
        formatted += artist + seperator +" "
    return formatted[:-2].strip()


def set_audio_tags(filename, media: AbstractMediaItem, seperator: str):
    # logger.info(
    #     f"Setting tags for audio media at "
    #     "'{filename}', mediainfo -> '{metadata}'"
    #     )
    type_ = 'track'
    tags = music_tag.load_file(filename)
    # TODO: Fix metadata
    for key in metadata.keys():
        value = metadata[key]
        if key == 'artists':
            tags['artist'] = conv_artist_format(value, )
        elif key in ['name', 'track_title', 'tracktitle']:
            tags['tracktitle'] = value
        elif key in ['album_name', 'album']:
            tags['album'] = value
        elif key in ['year', 'release_year']:
            tags['year'] = value
        elif key in ['discnumber', 'disc_number', 'disknumber', 'disk_number']:
            tags['discnumber'] = value
        elif key in ['track_number', 'tracknumber']:
            tags['tracknumber'] = value
        elif key == 'lyrics':
            tags['lyrics'] = value
        elif key == 'genre':
            if 'Podcast' in value or 'podcast' in value:
                type_ = 'episode'
            tags['genre'] = conv_artist_format(value)
        elif key in ['total_tracks', 'totaltracks']:
            tags['totaltracks'] = value
        elif key in ['total_discs', 'totaldiscs', 'total_disks', 'totaldisks']:
            tags['totaldiscs'] = value
        elif key == 'isrc':
            tags['isrc'] = value
    tags['comment'] = f'id[spotify.com:{type_}:{media.id}]'
    tags.save()


def set_music_thumbnail(filename, image: bytes):
    # logger.info(f"Set thumbnail for audio media at '{filename}' with '{image_url}'")
    img = Image.open(BytesIO(image))
    buf = BytesIO()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(buf, format='png')
    buf.seek(0)
    tags = music_tag.load_file(filename)
    tags['artwork'] = buf.read()
    tags.save()

def convert_media(ffmpeg_path: os.PathLike, source: Path, destination: Path, ffmpeg_args: str, bitrate: int = 44100) -> os.PathLike:
    command: list = [
        ffmpeg_path,
        '-i', str(source)
    ]
    # If the media format is set to ogg, just correct the downloaded file
    # and add tags
    if destination.suffix == '.ogg':
        command = command + ['-c', 'copy']
    else:
        command = command + ['-ar', str(bitrate), '-ac', '2', '-b:a', f'{bitrate}k']
    if int(os.environ.get('SHOW_FFMPEG_OUTPUT', 0)) == 0:
        command = command + \
                  ['-loglevel', 'error', '-hide_banner', '-nostats']
    # Add user defined parameters
    for param in ffmpeg_args:
        command.append(param)
    # Add output parameter at last
    command.append(str(destination))
    print(' '.join(command))
    subprocess.check_call(command, shell=False)
    return destination
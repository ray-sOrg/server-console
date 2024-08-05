from extensions import db


class WeddingMusic(db.Model):
    __tablename__ = 'wedding_music'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    artist = db.Column(db.String(100), nullable=False)
    album = db.Column(db.String(100))
    path = db.Column(db.String(200), nullable=False, unique=True)

    def __init__(self, title, artist, album, path):
        self.title = title
        self.artist = artist
        self.album = album
        self.path = path

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'path': self.path
        }

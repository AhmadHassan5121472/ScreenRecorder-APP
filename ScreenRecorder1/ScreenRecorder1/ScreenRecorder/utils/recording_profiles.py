class RecordingProfiles:
    PROFILES = {
        "Low Quality": {"fps": 24, "video_bitrate": "2M"},
        "Standard": {"fps": 30, "video_bitrate": "5M"},
        "High Quality": {"fps": 60, "video_bitrate": "10M"},
        "Custom": {"fps": 30, "video_bitrate": "5M"},
    }

    @classmethod
    def get_profile(cls, name):
        return cls.PROFILES.get(name, cls.PROFILES["Standard"]).copy()

    @classmethod
    def get_names(cls):
        return list(cls.PROFILES)

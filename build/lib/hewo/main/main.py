from hewo.main.window import MainWindow
from hewo.settings import SettingsLoader
from hewo.objects.hewo import HeWo
from hewo.objects.multimedia import MultimediaLayout

LOADER = SettingsLoader()

def main():
    window_settings =     LOADER.load_settings("hewo.settings.window")
    hewo_settings =       LOADER.load_settings("hewo.settings.hewo")
    multimedia_settings = LOADER.load_settings("hewo.settings.multimedia")
    # build layouts
    main_window = MainWindow(settings=window_settings)
    hewo_layout = HeWo(settings=hewo_settings)
    multimedia_layout = MultimediaLayout(settings=multimedia_settings)
    main_window.layout_dict = {
        "hewo": hewo_layout,
        "media": multimedia_layout
    }
    main_window.active_layout = window_settings["active_layout"]
    main_window.run()

if __name__ == "__main__":
    main()

# Destroys instances of the dialog before recreating it
# This has to go first, before modules are reloaded or the ui var is re-declared.
try:
    ui.close()
except:
    pass

# --------------------
#       Modules
# --------------------

# PySide 2
from PySide2.QtUiTools import QUiLoader
import PySide2.QtWidgets as QtW
from PySide2.QtCore import QFile

# Import PyMXS, MaxPlus, and set up shorthand vars
import pymxs
import MaxPlus

# Misc
import sys
import os

# --------------------
#      UI Class
# --------------------


class BakeAnimUI(QtW.QDialog):

    def __init__(self, ui_file, pymxs, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param runtime: The pymxs runtime
        :param parent: The main Max Window
        """
        # Init QtW.QDialog
        super(BakeAnimUI, self).__init__(parent)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._pymxs = pymxs
        self._parent = parent

        # ---------------------------------------------------
        #                     Main Init
        # ---------------------------------------------------

        # UI Loader

        ui_file = QFile(self._ui_file_string)
        ui_file.open(QFile.ReadOnly)

        loader = QUiLoader()
        self._widget = loader.load(ui_file)

        ui_file.close()

        # Attaches loaded UI to the dialog box

        main_layout = QtW.QVBoxLayout()
        main_layout.addWidget(self._widget)

        self.setLayout(main_layout)

        # Titling

        self._window_title = "Bake All Anim v01"
        self.setWindowTitle(self._window_title)

        # ---------------------------------------------------
        #                   Widget Setup
        # ---------------------------------------------------

        # Frame Range
        self._spn_start = self.findChild(QtW.QSpinBox, 'spn_start')
        self._spn_end = self.findChild(QtW.QSpinBox, 'spn_end')
        self._spn_nth = self.findChild(QtW.QSpinBox, 'spn_nth')
        self._btn_range = self.findChild(QtW.QPushButton, 'btn_updateRange')
        self._chk_pad = self.findChild(QtW.QCheckBox, 'chk_pad')

        # Track Selection
        self._box_tracks = self.findChild(QtW.QWidget, 'box_tracks')
        self._btn_tracks = self.findChild(QtW.QPushButton, 'btn_updateTracks')

        # Bake
        self._btn_bake = self.findChild(QtW.QPushButton, 'btn_getBaked')
        self._bar_progress = self.findChild(QtW.QProgressBar, 'bar_progress')
        self._lbl_status = self.findChild(QtW.QLabel, 'lbl_status')

        # ---------------------------------------------------
        #                Function Connections
        # ---------------------------------------------------
        # This section is sparse because we don't worry about fetching and validating other settings until we bake.

        # Frame Range
        self._btn_range.pressed.connect(self._update_range)

        # Track Selection
        self._btn_tracks.pressed.connect(self._update_tracks)

        # Bake
        self._btn_bake.pressed.connect(self._bake)

        # ---------------------------------------------------
        #                  Parameter Setup
        # ---------------------------------------------------

        self._options = {'start': 0,
                         'end': 100,
                         'nth': 1,
                         'pad': False}

        # ---------------------------------------------------
        #                   End of Init

    # ---------------------------------------------------
    #                  Private Methods
    # ---------------------------------------------------

    def _update_range(self):
        _rt = self._pymxs.runtime
        self._spn_start.setValue(_rt.animationRange.start)
        self._spn_end.setValue(_rt.animationRange.end)


    def _update_tracks(self):
        """
        Updates the Track Selection box with a list of unique track names
        """
        _rt = self._pymxs.runtime
        tracks = []
        layout = self._box_tracks.layout()

        # Get track list from current selection
        for obj in _rt.getCurrentSelection():
            tracks = self._get_keyed_subtracks(obj, tracks)

        # Clear the UI track list, repopulate with tracks we found
        for i in range(layout.count()):
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        index = 0
        for track in tracks:
            layout.addWidget(QtW.QCheckBox(track.name))
            widget = layout.itemAt(index).widget()
            widget.setChecked(True)
            index += 1

        layout.addStretch()


    def _bake(self):
        print "Bake"


    def _get_keyed_subtracks(self, track, list=[]):
        """
        Crawl through track heirarchy, building a list of animated tracks.  Exclude Position and Rotation parent tracks.
        :param track: The track to start crawling from - also used when called recursively
        :param list: The list of animated tracks, should start blank.
        :return: A list of all (unique) animated track objects below the initial track.
        """
        _rt = self._pymxs.runtime

        ignore = ['Transform', 'Position', 'Rotation']

        # Only add this track to the list if it's a SubAnim, has a controller, and has been animated
        if _rt.iskindof(track, _rt.SubAnim) and _rt.iscontroller(track.controller) and track.isanimated:
            if track not in list and track.name not in ignore:
                list.append(track)

        # Always call self recursively on all children of this track
        # Note: SubAnim list is 1-indexed.  Thanks, Autodesk.
        for i in range(1, track.numsubs + 1):
            list = self._get_keyed_subtracks(_rt.getSubAnim(track, i), list)

        return list


def bake_anim(obj, start, end, n):
    tracks = get_keyed_subtracks(obj)
    print "%s has %d keyed tracks" % (obj.name, len(tracks))
    if len(tracks) == 0:
        return

    for track in tracks:
        print "Caching %s..." % track.name
        # Cache track values _at each frame, every n'th frame
        anim = []
        for t in range(start, end, n):
            with _at(t):
                anim.append(track.value)

        # Now clear the track and write cached keys
        _rt.deleteKeys(track)

        anim_index = 0
        with _animate(True):
            for t in range(start, end, n):
                # print anim[anim_index]
                with _at(t):
                    track.controller.value = anim[anim_index]
                anim_index += 1

        print "Baked %s" % track.name


# --------------------
#    Dialog Setup
# --------------------

# Path to UI file
_uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\bakeAllAnim_v01.ui"
_app = MaxPlus.GetQMaxMainWindow()
ui = BakeAnimUI(_uif, pymxs, _app)

# Punch it
ui.show()

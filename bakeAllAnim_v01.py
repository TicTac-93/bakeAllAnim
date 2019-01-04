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

# PyMXS variable setup
_rt = pymxs.runtime
_at = pymxs.attime
_animate = pymxs.animate

# --------------------
#      UI Class
# --------------------

class bakeAnimUI(QtW.QDialog):

    def __init__(self, ui_file, runtime, parent=MaxPlus.GetQMaxMainWindow()):
        """
        The Initialization of the main UI class
        :param ui_file: The path to the .UI file from QDesigner
        :param runtime: The pymxs runtime
        :param parent: The main Max Window
        """
        # Init QtW.QDialog
        super(bakeAnimUI, self).__init__(parent)

        # ---------------------------------------------------
        #                    Variables
        # ---------------------------------------------------

        self._ui_file_string = ui_file
        self._rt = runtime
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

        # ---------------------------------------------------
        #                   End of Init


# ===========================
#           Logic
# ===========================

def get_keyed_subtracks(track, list=[]):
    """
    Crawl through track heirarchy, building a list of animated tracks.
    :param track: The track to start crawling from - also used when called recursively
    :param list: The list of animated tracks, should start blank.
    :return: A list of all animated track objects below the initial track.
    """
    # Only add this track to the list if it's a SubAnim, has a controller, and has been animated
    if _rt.iskindof(track, _rt.SubAnim) and _rt.iscontroller(track.controller) and track.isanimated:
        if track not in list:
            list.append(track)

    # Always call self recursively on all children of this track
    # Note: SubAnim list is 1-indexed.  Thanks, Autodesk.
    for i in range(1, track.numsubs + 1):
        list = get_keyed_subtracks(_rt.getSubAnim(track, i), list)

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


# start = _rt.animationRange.start
# end = _rt.animationRange.end
# n = 3
#
# print "Start: %d\rEnd: %d\rN: %d" % (start, end, n)
#
# for obj in _rt.getCurrentSelection():
#     print "-------------------\rChecking %s..." % obj.name
#     bake_anim(obj, start, end, n)


# --------------------
#    Dialog Setup
# --------------------

# Path to UI file
_uif = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + "\\bakeAllAnim_v01.ui"
_app = MaxPlus.GetQMaxMainWindow()
ui = bakeAnimUI(_uif, _rt, _app)

# Punch it
ui.show()

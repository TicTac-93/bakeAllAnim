# bakeAllAnim
A script for 3ds Max to bake any animated track, with options for every-nth-frame and track selection.

Install by copying the bakeAllAnim folder to your 3ds Max scripts directory.
Run in 3ds Max using with the MaxScript snippet:
`python.ExecuteFile @"C:\path\to\bakeAllAnim\bakeAllAnim.py"`


-----

To use, run the script and select the objects you want to bake.

Set your frame range with the spinners at the top of the UI, optionally setting the "Nth Frame" value.

Select which types of tracks you want to bake from the "Track Options" menu.

Click "Get Tracks From Selection" and *uncheck* any tracks that you do *not* want to be baked. 
 Note that any tracks that are baked will lose animation outside of the frame range!

To actually bake the selected tracks, click "Get Baked".  This may take a while if you have a large number of objects selected, so please be patient.  The loading bar should update, but if the UI freezes there's not much I can do.
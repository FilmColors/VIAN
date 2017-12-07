.. _segmentation:

Segmentation
============

.. toctree::
   :maxdepth: 2

   create_segmentation
   create_segment
   changing_main_segmentation
   locking_segmentations
   exporting_segmentations


Segmentations are the key-entity in VIAN (and most other Annotation Applications anyway). Each Segmentation created in VIAN,
is shown in the *Outliner* in the *Segmentation* category. Essentially a Segmentation consists of [0, ... , n] *Segments*,
where each Segment has a Name, ID and a Annotation Body, this is, an piece of text describing the Segment.

One Segmentation in a VIAN project is always referred to as the **Main Segmentation**, this is the one currently used for
sorting the Screenshots. How to change the current Main Segmentation is explained in :ref:`changing_main_segmentation`.

Screenshots are automatically ordered and reordered according to the Main Segmentation.



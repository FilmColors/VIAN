Experiments
===========

Experiments are maybe VIAN's most powerful tools. It's main purpose is to classify collected data in during the segmentation
and annotation phase.

The concept is the following:
Once one has collected data in VIAN, that is, creating Segments, Stills or Annotations, he wants to classify
this data by specific properties.
An experiment consists of a set of rules about how and which data should be classified. It defines which data should
be classified by which **Vocabularies** and which **Classification Objects**.

.. note:: **Following Example should elaborate the concept:**
   Bob has just segmented a film called "Alice in Wonderland" into temporal segments in the segmentation called "Main Segmentation"
   and now wants to classify them by two attributes: If the color of a segment is saturated or desaturated
   and if the mediated emotion of the scene is happy, thrilling or sad.

   In VIAN he would thus create two **Vocabularies**: "Saturation" and "Emotion"
   "Saturation" contains two word: "saturated" and "desaturated",
   "Emotion" contains three: "happy", "thrilling" and "sad".

   Since Bob knows that the saturation of the protagonist's dress is a completely different thing than the one of the
   supporting actors, he want's to classify them seperately.
   He would thus create two **Classification Objects** "Protagonist" and "Support" and classify both by the vocabulary
   "Saturation". He then creates a third Classification Object "Global" for the emotion since it is not focused on the
   protagonist in his case.

   Finally he would set for all three classification objects to target his "Main Segmentation".
   VIAN will now create a questionnaire for all segments, which he can classify.



.. toctree::
   :maxdepth: 4

   project_management/project_management




* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
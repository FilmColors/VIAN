.. _experiments:

Experiments
===========

.. toctree::
   :maxdepth: 4

   creating_experiments.rst

************
Introduction
************
Often, one does not only want to segment a film into temporal and spatial segments using VIANs
:ref:`segmentation`, :ref:`screenshots` or :ref:`annotation` functionality, but also **classify** these by means of tags.
The intention behind this to structure the qualitative analysis using well defined sets of words, which allows querying
and visualization of the collected data in a later stage. VIAN uses the term **classification** to describe this task,
some would however call this tagging.

VIAN comes supports this using its **experiments**. An Experiment simply encapsulates everything related to
classification, making it possible to perform several unrelated classifications within one project.

The short an Experiment can be described as follows:
Once one has collected data in VIAN, that is, creating Segments, Stills or Annotations, he wants to classify
this data by specific vocabularies.
An experiment consists of a set of rules about how and which data should be classified. It defines which data should
be classified by which **vocabularies** and which **classification objects**.


.. note:: **Following Example should elaborate the concept:**
   Bob has just segmented a film called "Alice in Wonderland" into temporal segments in the segmentation called "Main Segmentation"
   and now wants to classify them by two attributes: If the color of a segment is saturated or desaturated
   and if the mediated emotion of the scene is happy, thrilling or sad.

   In VIAN he would thus create two **vocabularies**: "Saturation" and "Emotion"
   "Saturation" contains two word: "saturated" and "desaturated",
   "Emotion" contains three: "happy", "thrilled" and "sad".

   Since Bob knows that the saturation of the protagonist's dress is a completely different thing than the one of the
   supporting actors, he want's to classify them seperately.
   He would thus create two **classification objects** "Protagonist" and "Support" and classify both by the vocabulary
   "Saturation". He then creates a third Classification Object "Global" for the emotion since it is not focused on the
   protagonist in his case.

   Finally he would set for all three classification objects to target his "Main Segmentation".
   VIAN will now create a questionnaire for all segments, which he can classify.







* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

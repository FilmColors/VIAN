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
The intention behind this is to structure the qualitative analysis using well defined sets of words, which allows querying
and visualization of the collected data in a later stage. VIAN uses the term **classification** to describe this task,
some would however call this tagging.

VIAN supports this using a techinique, called **experiments**. An Experiment simply encapsulates everything related to
classification, making it possible to perform several unrelated classifications within one project.

In short, an Experiment can be described as follows:
Once one has collected data in VIAN, that is, creating Segments, Stills or Annotations, one wants to classify
this data by specific vocabularies.
An experiment consists of a set of rules about how and which data should be classified. It defines which data should
be classified by which **vocabularies** and which **classification objects**.


.. note:: **Following Example should elaborate the concept:**
   Bob has just segmented a film called "Alice in Wonderland" into temporal segments in the segmentation called "Main Segmentation"
   and now wants to classify them by two attributes: If the color of a segment is saturated or desaturated
   and if the mediated emotion of the scene is happy, thrilling or sad.

   In VIAN he would thus create two **vocabularies**: "Saturation" and "Emotion"
   "Saturation" contains two words: "saturated" and "desaturated",
   "Emotion" contains three: "happy", "thrilled" and "sad".

   Since Bob knows that the saturation of the protagonist's dress is a completely different thing than the one of the
   supporting actors, he want's to classify them seperately.
   He would thus create two **classification objects** "Protagonist" and "Support" and classify both by the vocabulary
   "Saturation". He then creates a third Classification Object "Global" for the emotion since it is not focused on the
   protagonist in his case.

   Finally he would set for all three classification objects to target his "Main Segmentation".
   VIAN will now create a questionnaire for all segments, which he can classify.


********************
Creating Experiments
********************
.. _creating_experiments:

To create a new Experiment, do the following:

    1. Go to **Create/Create Experiment**.
    2. Open the experiment editor either by clicking |icon_experiment_editor| in the toolbar, or via **Windows/Experiment Editor**.
    3. Open the outliner by either clicking |icon_outliner| in the toolbar, **Alt + O** or via **Windows/Outliner**.
    4. In the outliner select the new experiment.
    5. In the experiment editor open the **General** tab to rename the experiment to your needs.


***********************
Configuring Experiments
***********************
.. _configuring_experiments:

Setting up an experiment can feel a bit complicated at the beginning, but will become more intuitive once you understood,
VIAN's way of looking at things.

Once you have configured your experiment as described in :ref:`_creating_experiments` you can edit the experiment
in the experiment editor. You should now see this widget:

.. figure:: experiment_editor.jpg
   :scale: 80 %
   :align: center
   :alt: Experiment editor in VIAN.


To add classification objects, do the following:

    1. Open the experiment editor either by clicking |icon_experiment_editor| in the toolbar, or via **Windows/Experiment Editor**.
    2. In the **Classification** tab, add a classification object by typing its name into the textbox on the bottom.
    3. On the right side, select the **Vocabularies** tab.
    4. In **Attached Vocabularies** tick all vocabularies with which you want to classify the created classification object.


.. note:: **Classification Objects**
    A classification object may be both a conceptual or true object which you want to classify, and may have a pixel
    representation within the film material. E.g. A classification object could be named *Figure* or *Ground*,
    since only the *Figure* can have an emotional state, the vocabulary *Emotion* would only be used to classify *Figure*.
    A conceptual classification object could for example be *Soundtrack*.



.. |icon_experiment_editor| image:: ../../../../qt_ui/icons/icon_settings_plot.png
   :height: 20px
   :width: 20px

.. |icon_outliner| image:: ../../../../qt_ui/icons/icon_outliner.png
   :height: 20px
   :width: 20px

.. seealso::

   * :ref:`new_project`
   * :ref:`import_elan_projects`
   * :ref:`changing_movie_paths`



* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


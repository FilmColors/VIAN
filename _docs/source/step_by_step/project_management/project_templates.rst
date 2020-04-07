.. _project_templates:



Project Templates
*****************

Templates give you the ability to keep specific setups between multiple projects.
A Template stores the empty Segmentation, Annotation Layers, Vocabularies and Node Scripts,
and can be imported on project creation.

1. Go to File/Export/Project Template.
2. The Export Project Template Dialog should appear.
3. Fill out the Form.
4. Click on Export to finish the process.

.. note:: **Options**

   1. **Name**, how the template should appear in the "New Project Dialog"
   2. **Include**, which entities of your project should be exported. (Often you would only want to include the parts relevant for classification, i.e. the Vocabular and the Experiments)


.. figure:: export_template.png
   :scale: 80 %
   :align: center
   :alt: map to buried treasure

   The Export Template Dialog


Once a template has been created, it can be used when creating a :ref:`new_project`.
If you want to send the template to others, it can be found in folder «templates» in the VIAN directory (normally under «Documents»):

.. figure:: path_to_templates.png
   :scale: 80 %
   :align: center
   :alt: map to buried treasure

   The templates folder in the VIAN directory


.. seealso::

   * :ref:`new_project`
   * :ref:`import_elan_projects`
   * :ref:`changing_movie_paths`


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

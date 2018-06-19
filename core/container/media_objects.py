from core.data.enums import MEDIA_OBJECT, MediaObjectType
from core.data.interfaces import IProjectContainer, IHasName, IHasMediaObject
from core.data.computation import *

class AbstractMediaObject(IProjectContainer, IHasName):
    """
    :var name: The Name of this Object
    :var container: The Container it belongs to
    :var dtype: The Type of data stored in this MediaObject
    """
    def __init__(self, name, container:IHasMediaObject, dtype):
        IProjectContainer.__init__(self)
        self.name = name
        self.container = container
        self.dtype = dtype

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_type(self):
        return MEDIA_OBJECT

    def serialize(self):
        data = dict(
            name = self.name,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def delete(self):
        pass

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self

    def preview(self):
        pass


class FileMediaObject(AbstractMediaObject):
    """
        :var name: The Name of this Object
        :var container: The Container it belongs to
        :var dtype: The Type of data stored in this MediaObject
        :var file_path: The File Path to this object's source
        """
    def __init__(self, name, file_path, container, dtype):
        super(FileMediaObject, self).__init__(name, container, dtype)
        self.file_path = file_path

    def serialize(self):
        data = dict(
            name = self.name,
            file_path = self.file_path,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.file_path = serialization['file_path']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self

    def delete(self):
        try:
            os.remove(self.file_path)
        except Exception as e:
            print(e)
            pass

    def preview(self):
        success = open_file(self.file_path)
        # TODO Files that are not here anymore should be asked to be removed, or linked again


class DataMediaObject(AbstractMediaObject):
    """
        :var name: The Name of this Object
        :var container: The Container it belongs to
        :var dtype: The Type of data stored in this MediaObject
        :var data: The Data Dict of this object
        """
    def __init__(self, name, data, container, dtype):
        super(DataMediaObject, self).__init__(name, container, dtype)
        self.data = data

    def serialize(self):
        data = dict(
            name = self.name,
            data = self.data,
            unique_id = self.unique_id,
            dtype = self.dtype.value
        )
        return data

    def deserialize(self, serialization):
        self.name = serialization['name']
        self.data = serialization['data']
        self.unique_id = serialization['unique_id']
        self.dtype = MediaObjectType(serialization['dtype'])
        return self


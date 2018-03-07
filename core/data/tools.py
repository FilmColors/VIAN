from core.data.containers import VIANProject

AUTO_SEGM_EVEN = 0
def auto_segmentation(project:VIANProject, mode, n_segment = -1, segm_width = 10000):
    duration = project.movie_descriptor.duration

    if mode == AUTO_SEGM_EVEN:
        if n_segment < 0:
            n_segment = int(duration / segm_width)
        else:
            segm_width = int(duration / n_segment)

        segmentation = project.create_segmentation("Auto Segmentation", False)
        for i in range(n_segment):
            segmentation.create_segment(i * segm_width, i * segm_width + segm_width, dispatch=False)









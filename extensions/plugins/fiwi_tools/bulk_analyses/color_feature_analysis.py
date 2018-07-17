from core.data.headless import *
from core.container.project import *
from extensions.plugins.fiwi_tools.filemaker2projectspy import load_project_list
from core.analysis.color_feature_extractor import ColorFeatureAnalysis
from core.data.computation import labels_to_binary_mask

def compute_features(movie_path, frame_idx, mask, label, scr, class_obj):
    cap = cv2.VideoCapture(movie_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    ret, frame = cap.read()
    frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

    if mask is not None:
        indices = np.where(mask == label)
        frame = frame[indices]
        frame_lab = frame_lab[indices]
    else:
        frame = np.reshape(frame, (frame.shape[0] * frame.shape[1], 3))
        frame_lab = np.reshape(frame, (frame.shape[0] * frame.shape[1], 3))

    colors_bgr = np.mean(frame, axis=0)
    colors_lab = np.mean(frame_lab, axis=0)

    saturation_l = lab_to_sat(lab=colors_lab, implementation="luebbe")
    saturation_p = lab_to_sat(lab=colors_lab, implementation="pythagoras")


    colors_bgr = np.nan_to_num(colors_bgr)
    colors_lab = np.nan_to_num(colors_lab)
    saturation_l = np.nan_to_num(saturation_l)
    saturation_p = np.nan_to_num(saturation_p)

    return IAnalysisJobAnalysis(
        name="Color-Features",
        results=dict(color_lab=colors_lab,
                     color_bgr=colors_bgr,
                     saturation_l=saturation_l,
                     saturation_p=saturation_p
                     ),
        analysis_job_class=ColorFeatureAnalysis,
        parameters=dict(resolution=50),
        container=scr,
        target_classification_object=class_obj
    )

if __name__ == '__main__':
    projects = load_project_list()
    project, mw = load_project_headless(projects[0][0])

    class_obj_fg = project.experiments[0].get_classification_object_by_name("Foreground")
    class_obj_bg = project.experiments[0].get_classification_object_by_name("Background")
    class_obj_glob = project.experiments[0].get_classification_object_by_name("Global")

    project.inhibit_dispatch = True
    analyses = []
    for i, scr in enumerate(project.screenshots):
        if i > 10:
            break
        print(i, "/", len(project.screenshots))
        multi_mask = scr.get_connected_analysis(SemanticSegmentationAnalysis)[0].get_adata()['mask']
        fg_mask = labels_to_binary_mask(multi_mask, class_obj_fg.semantic_segmentation_labels[1])
        fg_features = compute_features(project.movie_descriptor.movie_path, scr.frame_pos, fg_mask,
                         1, scr, class_obj_fg)
        bg_mask = labels_to_binary_mask(multi_mask, class_obj_bg.semantic_segmentation_labels[1])
        bg_features = compute_features(project.movie_descriptor.movie_path, scr.frame_pos, bg_mask,
                         1, scr, class_obj_bg)
        glob_mask = labels_to_binary_mask(multi_mask, class_obj_glob.semantic_segmentation_labels[1])
        glob_features = compute_features(project.movie_descriptor.movie_path, scr.frame_pos, glob_mask,
                         1, scr, class_obj_glob)

        analyses.append(fg_features)
        analyses.append(bg_features)
        analyses.append(glob_features)
    project.add_analyses(analyses)




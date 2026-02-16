"""
The heuristic file controls how information about the DICOMs is used to convert
to a file system layout (e.g., BIDS).
See: https://heudiconv.readthedocs.io/en/latest/heuristics.html

Author:      José C. García Alanis
Date:        February 2026
Affiliation: Neuromodulation Unit, Philipps-Universität Marburg

Description:
    This script defines a heuristic for organizing neuroimaging data into a
    BIDS-compliant structure using templates for anatomical, field map,
    and resting-state functional MRI sequences. It is intended for use with
    tools like HeuDiConv to facilitate reproducible data organization.

Usage:
    Place this script in your HeuDiConv workflow and run it on DICOM datasets.
    Customize sequence descriptions as needed to match your acquisition protocol.

Requirements:
    This script assumes specific naming and dimensional patterns in the
    sequence descriptions. Update conditions if protocols change.

References:
    Thus file is based on the walkthrough by Stanford Center for Reproducible
    Neuroscience:
    BIDS Tutorial Series: HeuDiConv Walkthrough (May 17, 2018)
    https://reproducibility.stanford.edu/bids-tutorial-series-part-2a/
"""


def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    """
    Create a BIDS-compatible naming key for a sequence.

    Parameters:
        template (str): BIDS format string with placeholders.
        outtype (tuple): Output file types, default is ('nii.gz',).
        annotation_classes (list or None): Optional annotations.

    Returns:
        tuple: (template, outtype, annotation_classes)
    """
    if template is None or not template:
        raise ValueError('Template must be a valid format string')
    return template, outtype, annotation_classes


def infotodict(seqinfo):
    """
    Heuristic evaluator for determining which runs belong to which modality.

    Parameters:
        seqinfo (list): A list of sequence information objects, each with
                        attributes like dim1, dim2, series_description, etc.

    Returns:
        dict: Mapping from BIDS keys to lists of sequence IDs.
    """
    t1w = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_T1w')
    fmap_b03d = create_key('sub-{subject}/{session}/fmap/sub-{subject}_{session}_fieldmap')
    func_rest = create_key('sub-{subject}/{session}/func/sub-{subject}_{session}_task-rest_run-0{item:01d}_bold')

    info = {
        t1w: [],
        fmap_b03d: [],
        func_rest: []
    }

    for idx, s in enumerate(seqinfo):

        # T1-weighted structural scan
        # Series description provided by scanner (can usually be found in dicom-header or dicominfo file)
        if (s.dim1 == 256) and (s.dim2 == 256) and (s.series_description == 'MPRAGE_SagACPC_1iso'):
            info[t1w].append(s.series_id)

        # B0 field map scan
        # Series description provided by scanner (can usually be found in dicom-header or dicominfo file)
        if (s.dim3 == 208) and (s.dim4 == 1) and (s.series_description == 'B0_Fieldmap3D_AxACPC'):
            info[fmap_b03d].append(s.series_id)

        # Resting-state fMRI scan
        # Series description provided by scanner (can usually be found in dicom header or dicominfo file)
        if (s.dim1 == 128) and (s.dim2 == 128) and (s.series_description == 'RSfMRI_1500_30_2_1_iso30seq03'):
            info[func_rest].append(s.series_id)

    return info
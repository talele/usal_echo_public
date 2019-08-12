import pandas as pd
from d00_utils.db_utils import dbReadWriteClean, dbReadWriteViews, dbReadWriteMeasurement

def write_groundtruth(instanceidks):
    """Write ground truth volume and ejection fraction measurements for given instanceidks to schema."""
    io_clean = dbReadWriteClean()
    io_views = dbReadWriteViews()
    io_measurement = dbReadWriteMeasurement()
    
    # For measurement name and unit on the study level.
    measurement_abstract_rpt_df = io_clean.get_table("measurement_abstract_rpt")
    measurement_abstract_rpt_df = measurement_abstract_rpt_df.drop(['value'], axis=1)

    # For measurement values on the instance/indexinmglist/meassequence level.
    a_measgraphref_df = io_clean.get_table("a_measgraphref")
    a_measgraphref_df = a_measgraphref_df.drop(['srinstanceidk', 'imagesopinstanceuid', 'measurementuid'], axis=1)

    # For instances with A2C/A4C views.
    instances_w_labels_df = io_views.get_table('instances_w_labels')
    instances_w_a2c_a4c_labels_df = instances_w_labels_df[(instances_w_labels_df['view']!='plax')]
    instances_w_a2c_a4c_labels_df = instances_w_a2c_a4c_labels_df[['studyidk', 'instanceidk', 'filename']]
    
    # All measurements values for A2C/A4C instances with measurement name and unit.
    merge_df = measurement_abstract_rpt_df.merge(a_measgraphref_df, on=['studyidk', 'measabstractnumber'])
    merge_df = merge_df.merge(instances_w_a2c_a4c_labels_df, on=['studyidk', 'instanceidk'])
    
    # To calculate ejection fraction, need gold-standard (MDD-ps4), non-negative end systole/diastole volumes.
    filter_df = merge_df[merge_df['name'].isin(['VTD(MDD-ps4)', 'VTS(MDD-ps4)'])]
    filter_df = filter_df[filter_df['value']>0]
    filter_df = filter_df[filter_df['instanceidk'].isin(instanceidks)]
    
    # Rename and reorder columns for measurement schema.
    rename_df = filter_df[['studyidk', 'instanceidk', 'filename', 'name', 'unitname', 'value', 'indexinmglist']]
    rename_df = rename_df.rename(
        columns={'studyidk': 'study_id', 'instanceidk': 'instance_id', 'filename': 'file_name', 'name': 'measurement_name', 'value': 'measurement_value', 'unitname': 'measurement_unit'})
    
    # Get median measurement over meassequence/indexinmglist.
    agg_dict = {"measurement_value": pd.Series.median, "measurement_unit": pd.Series.unique}
    volume_df = rename_df.groupby(['study_id', 'instance_id', 'file_name', 'measurement_name', 'indexinmglist']).agg(agg_dict).reset_index()
    volume_df = volume_df.groupby(['study_id', 'instance_id', 'file_name', 'measurement_name']).agg(agg_dict).reset_index()

    # Get diastole and systole volumes that are in the same instances.
    diastole_df = volume_df[volume_df['measurement_name'].str.contains('VTD')]
    systole_df = volume_df[volume_df['measurement_name'].str.contains('VTS')]
    
    diastole_df = diastole_df.drop(['measurement_name', 'measurement_unit'], axis=1)
    systole_df = systole_df.drop(['measurement_name', 'measurement_unit'], axis=1)
    
    diastole_df = diastole_df[diastole_df['instance_id'].isin(systole_df['instance_id'].unique())]
    systole_df = systole_df[systole_df['instance_id'].isin(diastole_df['instance_id'].unique())]
    
    # Get ejection fraction where diastole volume is no less than systole volume.
    ef_df = diastole_df.merge(systole_df, on=['study_id', 'instance_id'], suffixes=['_diastole', '_systole'])
    ef_df = ef_df[ef_df['measurement_value_diastole']>=ef_df['measurement_value_systole']]
    
    ef_df['file_name'] = ef_df['file_name_diastole']
    ef_df['measurement_name'] = 'FE(MDD-ps4)'
    ef_df['measurement_value'] = (ef_df['measurement_value_diastole']-ef_df['measurement_value_systole'])/ef_df['measurement_value_diastole']*100
    ef_df['measurement_unit'] = '%'
    
    ef_df = ef_df.drop(['file_name_diastole', 'measurement_value_diastole', 'file_name_systole', 'measurement_value_systole'], axis=1)
    
    ground_truth_df = volume_df.append(ef_df)
    io_measurement.save_to_db(ground_truth_df, "ground_truths")
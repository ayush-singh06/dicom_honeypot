from pydicom.data import get_testdata_file
filename = get_testdata_file("CT_small.dcm")
print("Filename:", filename)
if filename:
    from pydicom import dcmread
    ds = dcmread(filename)
    print("PatientName:", ds.PatientName)

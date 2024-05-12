def transform_length(file_size):
    if file_size >= 1024 * 1024 * 1024:
        file_size = f"{file_size/(1024*1024*1024):.2f} GB"
    elif file_size >= 1024 * 1024:
        file_size = f"{file_size/(1024*1024):.2f} MB"
    elif file_size >= 1024:
        file_size = f"{file_size/1024:.2f} KB"
    else:
        file_size = f"{file_size} B"
    return file_size

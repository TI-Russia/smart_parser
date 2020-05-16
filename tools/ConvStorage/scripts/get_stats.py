import logging
from ConvStorage.conversion_client import TDocConversionClient

if __name__ == '__main__':
    conv_client = TDocConversionClient(logging)
    print(conv_client.get_pending_all_file_size())

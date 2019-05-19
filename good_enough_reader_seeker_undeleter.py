# Prog 1 - displays the drives on your Windows computer. Code snippets
# from http://www.stackoverflow.com, http://docs.python.org, http://pjrc.com
# and elsewhere

import ctypes
import win32api
import os
import string

import os.path

kernel32 = ctypes.windll.kernel32
volumeNameBuffer = ctypes.create_unicode_buffer(1024)
fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)

serial_number = None
max_component_length = None
file_system_flags = None

# Globals that hold info about the flash drive we chose
USBFlashName = ""  # The label name of our drive
USBFlashVolName = "" # The full volume name for Windows
USBFlashSize = ""  # The size in GB
USBFlashNum = -1   # In the OS, what drive number we think this is
USBFLashDriveLetter = "" # A letter like C:, D:, etc,
text_output1 = ''
bman_path = 'C:\\Users\\fanni\\'

def findOurFlashDrive():
    global USBFlashName, USBFlashSize, USBFlashDriveLetter
    num = -1
    drives = win32api.GetLogicalDriveStrings()
    drives = drives.split('\000')[:-1]
    for i in range (0, len(drives)):
        volumeNameBuffer.value = ""
        fileSystemNameBuffer.value = ""
        rc = kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drives[i]),
                volumeNameBuffer,
                ctypes.sizeof(volumeNameBuffer),
                serial_number,
                max_component_length,
                file_system_flags,
                fileSystemNameBuffer,
                ctypes.sizeof(fileSystemNameBuffer)
        )
        print(i, drives[i], volumeNameBuffer.value, fileSystemNameBuffer.value)
        try:
            driveinfo = win32api.GetVolumeInformation(drives[i])
        except:
            driveinfo = ('','','','','')
        # driveinfo[4] should be the type of file system
        if driveinfo[0] != '':
            drivename = driveinfo[0]
        else:
            drivename = "(has no name)"
        if driveinfo[4] == "FAT32":
            _ = ctypes.c_ulonglong()
            total = ctypes.c_ulonglong()
            free = ctypes.c_ulonglong()
            kernel32.GetDiskFreeSpaceExW(drives[i], ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
            sizeinGB = round(total.value / 1000000000, 1)
            #print("Drive",i, "is named ",drivename," and is a ",sizeinGB,"GB ",driveinfo[4]," drive")
            if sizeinGB >= 8 and sizeinGB <= 32:
                num = i
                USBFlashName = drivename
                USBFlashSize = sizeinGB
                USBFlashDriveLetter = drives[i]
    return num

def readyToGo() :
    USBFlashNum = findOurFlashDrive()
    if USBFlashNum >= 0:
        print("We found a ",USBFlashSize,"GB drive named ",USBFlashName," as drive ", USBFlashNum,".")
        print("Is this the drive you want to work with?")
        q = input(" 'yes' or 'no'?")
        if q == "yes":
            goforit = True
        else:
            goforit = False
    else:
        goforit = False
        print("I was unable to locate a suitable FAT32 drive for this experiment. Please")
        print("format a USB flash drive between 8 and 32GB as FAT32.")
    return goforit

def read_a_sector(which_sector):
    global sector, sector_size, fd
    fd.seek(which_sector*sector_size, 0)
    data = fd.read(sector_size)
    #print("Got ",len(data)," bytes", which_sector, sector_size)
    sector = []
    for i in range(0, len(data)):
        sector.append(data[i])

def read_a_FAT(which_FAT):
    # This reads in the whole FAT. We might do this once - doing this for
    # each file read would be tedious
    global sector, sector_size, fd
    global bytes_per_sector, sectors_per_cluster, num_reserved_sectors
    global num_of_FATs, sectors_per_FAT, first_root_cluster
    global cluster, FAT

    # Figure out where the FAT begins
    start = num_reserved_sectors + ((which_FAT - 1) * sectors_per_FAT)
    print ("FAT ",which_FAT," starts at sector ",start)
    FAT = []
    for c in range(start,start+sectors_per_FAT):
        # print("Read sector ",c)
        read_a_sector(c)
        # display_sector(True)
        for i in range(0, len(sector)):
            FAT.append(sector[i])

def next_cluster(which_FAT, current_cluster):
    # Perhaps better for a quick file read, this function uses your current
    # cluster number, determines which FAT sector the entry is in and finds
    # that. Since we only support FAT32, each sector consists of 512/4 or
    # 128 cluster entries.
    global sector, sector_size, fd
    global bytes_per_sector, sectors_per_cluster, num_reserved_sectors
    global num_of_FATs, sectors_per_FAT, first_root_cluster
    global cluster

    # Figure out where the FAT begins
    start = num_reserved_sectors + ((which_FAT - 1) * sectors_per_FAT)
    # print ("FAT ",which_FAT," starts at sector ",start)
    # Which sector do we need?
    sector_within_FAT = int(current_cluster / 128)
    localFAT = []
    # print("Read sector ", start + sector_within_FAT)
    read_a_sector(start + sector_within_FAT)
    # display_sector(True)
    for i in range(0, len(sector)):
        localFAT.append(sector[i])
    # There are 128 32-bit values in this sector. We know where the byte starts
    # by taking the remainder of dividing the cluster by 128 (which gives us
    # a number from 0 to 127) and then multiply by 4 since there are 4 bytes
    # to each 32-bit integer
    bytenum = 4 * (current_cluster % 128)
    answer = (sector[bytenum+3] << 24) + (sector[bytenum+2] << 16) + \
             (sector[bytenum+1] << 8) + sector[bytenum]
    return answer

def read_a_cluster(which_cluster):
    global sector, sector_size, fd
    global bytes_per_sector, sectors_per_cluster, num_reserved_sectors
    global num_of_FATs, sectors_per_FAT, first_root_cluster
    global cluster

    # Figure out where the cluster begins
    start = num_reserved_sectors + (num_of_FATs * sectors_per_FAT) + \
            ((which_cluster - 2) * sectors_per_cluster)
    #print ("Cluster ",which_cluster," starts at sector ",start)
    cluster = []
    for c in range(start,start+sectors_per_cluster):
        #print("Read sector ",c)
        read_a_sector(c)
        #display_sector(True)
        for i in range(0, len(sector)):
            cluster.append(sector[i])

def prettyhex(n):
    # We don't want the '0x' in front and we want 2 chars always
    a = hex(n)
    a = "0"+a[2:]
    a = a[-2:]
    return a.upper()
    

def display_sector(ascii):
    global sector
    ascii_text = ""
    for i in range(0, 512):
        if sector[i] > 32 and sector[i] < 128:
            ascii_text = ascii_text + chr(sector[i])
        else:
            ascii_text = ascii_text + " "

        if 15 == i % 16:
            if ascii:
                print(prettyhex(sector[i]), end="")
                print("   " + ascii_text)
            else:
                print(prettyhex(sector[i]))
            ascii_text = ""
        else:
            print(prettyhex(sector[i])+" ",end="")

def display_dir_entry(dir_entry, cluster_offset):
    # Mostly from pjrc.com/tech/8051/ide/fat32.html
    global cluster
    global bman_path
    DIR_Name = ""
    for i in range(0,11):
        DIR_Name = DIR_Name + chr(cluster[cluster_offset + i])
    DIR_Attr = cluster[cluster_offset + 11]
    DIR_FstClusHI = cluster[cluster_offset + 20] + (cluster[cluster_offset + 21] << 8)
    DIR_FstClusLO = cluster[cluster_offset + 26] + (cluster[cluster_offset + 27] << 8)
    DIR_FstClus = DIR_FstClusLO + (DIR_FstClusHI << 16)
    DIR_FileSize = cluster[cluster_offset + 28] + (cluster[cluster_offset + 29] << 8) + (cluster[cluster_offset + 30] << 16) + (cluster[cluster_offset + 31] << 24)
    Attr_text = "      "
    if DIR_Attr & 0x01:
        Attr_text = 'R' + Attr_text[1:]
    if DIR_Attr & 0x02:
        Attr_text = Attr_text[0:1] + 'H' + Attr_text[2:]
    if DIR_Attr & 0x04:
        Attr_text = Attr_text[0:2] + 'S' + Attr_text[3:]
    if DIR_Attr & 0x08:
        Attr_text = Attr_text[0:3] + 'V' + Attr_text[4:]
    if DIR_Attr & 0x10:
        Attr_text = Attr_text[0:4] + 'D' + Attr_text[5:]
    if DIR_Attr & 0x20:
        Attr_text = Attr_text[0:5] + 'A' + Attr_text[6:]

    cloaked = False

    # Hide any of the long names which have VSHR all set
    cloaked = (DIR_Attr == 0x0f)
    # Hide any volume IDs
    cloaked = cloaked or DIR_Attr & 0x08
    # Hide any system files
    cloaked = cloaked or DIR_Attr & 0x04

    #if DIR_Name[0] == chr(0xE5) and not cloaked:
    #    print(Attr_text, " Entry ",dir_entry," was a file named ",DIR_Name, "that was ",DIR_FileSize," long starting at cluster ",DIR_FstClus)
    #elif DIR_Name[0] != chr(0x00) and not cloaked:
    #    print(Attr_text, " Entry ",dir_entry," is a file named ",DIR_Name," that is ",DIR_FileSize," long starting at cluster ",DIR_FstClus)
    
    if DIR_Name[0] == chr(0xE5) and not cloaked:
        print(" Entry ",dir_entry," was a file named ",DIR_Name, "that was ",DIR_FileSize," long starting at cluster ",DIR_FstClus)
    elif DIR_Name[0] != chr(0x00) and not cloaked:
        print(" Entry ",dir_entry," is a file named ",DIR_Name," that is ",DIR_FileSize," long starting at cluster ",DIR_FstClus)





def show_file_contents(dir_entry):
    # Mostly from pjrc.com/tech/8051/ide/fat32.html
    global cluster, FAT
    global text_output1
    global bman_path

    name_of_folder = 'Music'
    name_of_file=input('Enter the new name for the file you want to restore to an undeleted state: ')        
    name_of_folder = input('Enter the name of the directory you wish to place this file (Suggested: Music):')
        
    
    read_a_cluster(2)
    DIR_Name = ""
    cluster_offset = dir_entry * 32
    for i in range(0,11):
        DIR_Name = DIR_Name + chr(cluster[cluster_offset + i])
    DIR_Attr = cluster[cluster_offset + 11]
    DIR_FstClusHI = cluster[cluster_offset + 20] + (cluster[cluster_offset + 21] << 8)
    DIR_FstClusLO = cluster[cluster_offset + 26] + (cluster[cluster_offset + 27] << 8)
    DIR_FstClus = DIR_FstClusLO + (DIR_FstClusHI << 16)
    DIR_FileSize = cluster[cluster_offset + 28] + (cluster[cluster_offset + 29] << 8) + (cluster[cluster_offset + 30] << 16) + (cluster[cluster_offset + 31] << 24)

    cloaked = False

    full_file_name = os.path.join((str(bman_path) + str(name_of_folder)), name_of_file+".txt")
    win_fout1 = open(full_file_name,'w')

    

    # Read in FAT#1. FAT#2 should be the same so it doesn't matter
    # read_a_FAT(1)

    # Hide any of the long names which have VSHR all set
    cloaked = (DIR_Attr == 0x0f)
    # Hide any volume IDs
    cloaked = cloaked or DIR_Attr & 0x08
    # Hide any system files
    cloaked = cloaked or DIR_Attr & 0x04

    # Okay - now we can go for it if it's not cloaked
    if cloaked:
        print("Sorry, but I don't know to display that entry")
    else:
        bytes_displayed = 0
        print("We think that ",DIR_Name," starts at ",DIR_FstClus)
        current_cluster = DIR_FstClus
        read_a_cluster(current_cluster)
        cluster_ptr = 0
        while bytes_displayed < DIR_FileSize:
            text_output1 = str(text_output1) + str(chr(cluster[cluster_ptr]))
            if cluster_ptr == bytes_per_sector * sectors_per_cluster:
                # Read in a new cluster
                print('-----------bman: for debugging purposes: cluster_ptr == bytes_per_sector * sectors_per_cluster conditional has been met')
                print('-----------bman: for debugging purposes: cluster_ptr is: '+str(cluster_ptr))
                print("-----------bman: for debugging purposes: After reading cluster",current_cluster, end="")

                current_cluster = next_cluster(1, current_cluster)
                # print("the next cluster is ",current_cluster)
                read_a_cluster(current_cluster)
                cluster_ptr = 0;
            # print(chr(cluster[cluster_ptr]), end="")
            cluster_ptr = cluster_ptr + 1
            bytes_displayed = bytes_displayed + 1
            
            #if(len(text_output1) <= 125):
                #text_output1 = str(text_output1) + str(chr(cluster[cluster_ptr]))

        print("")
        print("Undeletion process should be taking place now: ")
        
                                         
        win_fout1.write(str(text_output1))
        win_fout1.close()
        text_output1 = ''



# -------------------------------------------------------
# -------------------------------------------------------







 
# This is where we do stuff
print("Let's see if we can find a drive...")
if not readyToGo():
    print("Hey, I tried...")
else:
    print("Yay!")
    print("Trying to open ",USBFlashDriveLetter)
    n = "\\\\.\\"+USBFlashDriveLetter[0]+":"
#    fd = os.fdopen(os.open(n, os.O_WRONLY|os.O_BINARY), "rb+")
    fd = open(n, 'rb+')

    # Make a list of empty sector information.
    sector_size = 512
    sector = []
    for i in range(0, sector_size):
        sector.append(0)
        
    # Sector 0 is the boot block and partition table
    read_a_sector(0)
    #display_sector(False)
    # The last 66 bytes are all er care about. There are 4 partition table
    # entries of 16 bytes each, and a 0x55AA at the end.

    sofarsogood = True  # If something fails along the way here, we set this to false

    if sofarsogood:
        if (sector[510] << 8 | sector[511]) != 0x55AA:
            sofarsogood = False
            print("Can't find the 55AA at the end of sector 0")
    if sofarsogood:
        # Since we're reading the logical drive, the Volume ID is the
        # first sector.
        #
        # Offset 11 (0x0B) is the bytes per sector and it's always 512
        bytes_per_sector = sector[11] + (sector[12] << 8)
        # Offset 13 (0x0D) is the # of sectors per cluster
        sectors_per_cluster = sector[13]
        # Offset 14 (0x0E) is the # of reserved sectors
        num_reserved_sectors = sector[14] + (sector[15] << 8)
        # Offset 16 (0x10) is the # of FATs (always 2)
        num_of_FATs = sector[16]
        # Offset 36 (0x24) is the # of sectors per FAT
        sectors_per_FAT = sector[36] + (sector[37] <<8) + (sector[38] <<16) + (sector[39] <<24)
        # Offset 44 (0x2C) is the first cluster of the root directory
        first_root_cluster = sector[44] + (sector[45] <<8) + (sector[46] <<16) + (sector[47] <<24)
        # Offset 510 is the signature and we already checked that
        print(bytes_per_sector," bytes per sector")
        print(sectors_per_cluster, " sectors per cluster")
        print(num_reserved_sectors, " reserved sectors")
        print(sectors_per_FAT, " sectors per FAT")
        print(first_root_cluster, " is the first root cluster")
        # Let's bail if the numbers don't make sense.
        if bytes_per_sector != 512:
            sofarsogood = False
            print("The bytes per sector MUST be 512!")
        valid_values = [1, 2, 4, 8, 16, 32, 64, 128]
        try:
            i = valid_values.index(sectors_per_cluster)
        except:
            sofarsogood = False
            print("We can't have ",sectors_per_cluster," sectors per cluster!")
        if num_of_FATs != 2:
            sofarsogood = False
            print("We have to have two FATs")
    if sofarsogood:            
        showfiles = True
        while showfiles:
            cluster_list=[]
            position_list=[]

            p_reply = input('To move directly onto the undeletion stage and skip the text search enter \"s\" now: ')
            if(p_reply.upper() == 'S'):
                break
            
            searchtext = input("What text do you want to search for?")
            
            max_text_spots = input("What is the max number of instances of this bit of text that our code should locate before moving on to stage 2?")
            max_text_spots = int(max_text_spots)
            current_text_spots=0
            # The text could span over a cluster boundary, so let's read in two
            # into a single string and search that. If we find it, we know what cluster
            # it started in.
            for c in range(2, 2 + (128 * sectors_per_FAT) - 1):
                
                # print("Checking clusters",c,",",c+1)
                read_a_cluster(c)  # This is the first one
                s = ""

                for i in range(0, sector_size * sectors_per_cluster):
                    s = s + chr(cluster[i])
                read_a_cluster(c+1)  # This is the second one
                for i in range(0, sector_size * sectors_per_cluster):
                    s = s + chr(cluster[i])
                p = s.find(searchtext)
                if p >= 0 and p < sector_size * sectors_per_cluster:
                    # p is relative to the string of two clusters.
                    # Only report if the string starts in the first cluster
                    print("Found at position ",p, " of cluster ",c)
                    current_text_spots=current_text_spots+1
                    cluster_list.append(int(c))
                    position_list.append(int(p))
                if(current_text_spots >= max_text_spots):
                    break

            # entry_list = []
            
            for count1, cluster_elem in enumerate(cluster_list):
                clustnum = 0
                position_num = 0
                max_text_search_buffer = 35
                characters_read_aloud = 0

                r_endpoint = 0

                # print('for debug purposes to check why certain passwords arent displaying-- printing characters_read_aloud: '+str(characters_read_aloud))

                
                # direct input if needed (currently commented out):
                # max_text_search_buffer = input("Enter the max number of characters at each discovered text location you want read out: ")

                # print("Valid cluster numbers are from 2 to",128*sectors_per_FAT)
                # clustnum = input("Cluster number or a range xx-xx (just Enter to quit) ")
                
                # print('Choose a position between 0 and '+str((bytes_per_sector*sectors_per_cluster)))
                # position_num = input("Enter the approximate position within the cluster")

                
                position_num=int(position_list[count1])
                clustnum=str(cluster_elem)
                print('this is the position of text item ' + str(count1) + ': ' + str(position_num))
                print('this is the cluster of text item ' + str(count1) + ': ' + str(clustnum))



                if len(clustnum) == 0:
                    showfiles = False
                    break
                if clustnum.find("-") < 0:
                    start = int(clustnum)
                    stop = start
                else:
                    start = int(clustnum[:clustnum.find("-")])
                    stop = int(clustnum[1+clustnum.find("-"):])
                if start < 2 or stop > 128*sectors_per_FAT:
                    showfiles = False
                if showfiles:
                    chars_this_line = 0;
                    cluster = []
                    for c in range(start, stop+1):
                        if(characters_read_aloud >= max_text_search_buffer):
                            characters_read_aloud = 0
                            break
                        read_a_cluster(c)
                        r_endpoint=int( (sectors_per_cluster*bytes_per_sector) + position_num )
                        if(r_endpoint >= int( (sectors_per_cluster*bytes_per_sector) )):
                            r_endpoint = int( (sectors_per_cluster*bytes_per_sector) )
                        else:
                            r_endpoint = int( (sectors_per_cluster*bytes_per_sector) + position_num )
                        for b in range((0 + position_num), (r_endpoint)):
                            if cluster[b] >= 32 and cluster[b] <=127:
                                print(chr(cluster[b]), end="")
                                chars_this_line = chars_this_line + 1
                                characters_read_aloud = characters_read_aloud + 1
                                # print('debugging-- char count = '+str(characters_read_aloud))
                                if chars_this_line == 80:
                                      print("")
                                      chars_this_line = 0
                                if(characters_read_aloud >= max_text_search_buffer):
                                    break
                    print("")

                




                
















                

# -------------------------------------------------------
# -------------------------------------------------------
# This is where we un-delete stuff
print("Let's see if we can find a drive...")
if not readyToGo():
    print("Hey, I tried...")
else:
    print("Yay!")
    print("Trying to open ",USBFlashDriveLetter)
    n = "\\\\.\\"+USBFlashDriveLetter[0]+":"
#    fd = os.fdopen(os.open(n, os.O_WRONLY|os.O_BINARY), "rb+")
    fd = open(n, 'rb+')

    # Make a list of empty sector information.
    sector_size = 512
    sector = []
    for i in range(0, sector_size):
        sector.append(0)
        
    # Sector 0 is the boot block and partition table
    read_a_sector(0)
    #display_sector(False)
    # The last 66 bytes are all er care about. There are 4 partition table
    # entries of 16 bytes each, and a 0x55AA at the end.

    sofarsogood = True  # If something fails along the way here, we set this to false

    if sofarsogood:
        if (sector[510] << 8 | sector[511]) != 0x55AA:
            sofarsogood = False
            print("Can't find the 55AA at the end of sector 0")
    if sofarsogood:
        # Since we're reading the logical drive, the Volume ID is the
        # first sector.
        #
        # Offset 11 (0x0B) is the bytes per sector and it's always 512
        bytes_per_sector = sector[11] + (sector[12] << 8)
        # Offset 13 (0x0D) is the # of sectors per cluster
        sectors_per_cluster = sector[13]
        # Offset 14 (0x0E) is the # of reserved sectors
        num_reserved_sectors = sector[14] + (sector[15] << 8)
        # Offset 16 (0x10) is the # of FATs (always 2)
        num_of_FATs = sector[16]
        # Offset 36 (0x24) is the # of sectors per FAT
        sectors_per_FAT = sector[36] + (sector[37] <<8) + (sector[38] <<16) + (sector[39] <<24)
        # Offset 44 (0x2C) is the first cluster of the root directory
        first_root_cluster = sector[44] + (sector[45] <<8) + (sector[46] <<16) + (sector[47] <<24)
        # Offset 510 is the signature and we already checked that
        print(bytes_per_sector," bytes per sector")
        print(sectors_per_cluster, " sectors per cluster")
        print(num_reserved_sectors, " reserved sectors")
        print(sectors_per_FAT, " sectors per FAT")
        print(first_root_cluster, " is the first root cluster")
        # Let's bail if the numbers don't make sense.
        if bytes_per_sector != 512:
            sofarsogood = False
            print("The bytes per sector MUST be 512!")
        valid_values = [1, 2, 4, 8, 16, 32, 64, 128]
        try:
            i = valid_values.index(sectors_per_cluster)
        except:
            sofarsogood = False
            print("We can't have ",sectors_per_cluster," sectors per cluster!")
        if num_of_FATs != 2:
            sofarsogood = False
            print("We have to have two FATs")
    if sofarsogood:
        read_a_cluster(2)
    # Now we have the first cluster of the directory. It breaks into 32 byte hunks
    if sofarsogood:
        entry_num = 0
        for i in range(0, (bytes_per_sector * sectors_per_cluster), 32):
            #print("Directory entry starts at offset ",i)
            if cluster[i] == 0:  # We reached the end of the directory
                break
            display_dir_entry(entry_num, i)
            entry_num = entry_num + 1
            num_files = entry_num  # The max number
            
    showfiles = True
    while showfiles:
        filenum = input("What text file can I show you? (just Enter to quit) ")
        if len(filenum) == 0:
            showfiles = False
            break
        n = int(filenum)
        if n <= num_files:
            show_file_contents(n)
            showfiles = False

    showfiles = True


# -------------------------------------------------------
# -------------------------------------------------------
































showfiles = True

# -------------------------------------------------------
# -------------------------------------------------------

 
# This is where we do stuff
print("Let's see if we can find a drive...")
if not readyToGo():
    print("Hey, I tried...")
else:
    print("Yay!")
    print("Trying to open ",USBFlashDriveLetter)
    n = "\\\\.\\"+USBFlashDriveLetter[0]+":"
#    fd = os.fdopen(os.open(n, os.O_WRONLY|os.O_BINARY), "rb+")
    fd = open(n, 'rb+')

    # Make a list of empty sector information.
    sector_size = 512
    sector = []
    for i in range(0, sector_size):
        sector.append(0)
        
    # Sector 0 is the boot block and partition table
    read_a_sector(0)
    #display_sector(False)
    # The last 66 bytes are all er care about. There are 4 partition table
    # entries of 16 bytes each, and a 0x55AA at the end.

    sofarsogood = True  # If something fails along the way here, we set this to false

    if sofarsogood:
        if (sector[510] << 8 | sector[511]) != 0x55AA:
            sofarsogood = False
            print("Can't find the 55AA at the end of sector 0")
    if sofarsogood:
        # Since we're reading the logical drive, the Volume ID is the
        # first sector.
        #
        # Offset 11 (0x0B) is the bytes per sector and it's always 512
        bytes_per_sector = sector[11] + (sector[12] << 8)
        # Offset 13 (0x0D) is the # of sectors per cluster
        sectors_per_cluster = sector[13]
        # Offset 14 (0x0E) is the # of reserved sectors
        num_reserved_sectors = sector[14] + (sector[15] << 8)
        # Offset 16 (0x10) is the # of FATs (always 2)
        num_of_FATs = sector[16]
        # Offset 36 (0x24) is the # of sectors per FAT
        sectors_per_FAT = sector[36] + (sector[37] <<8) + (sector[38] <<16) + (sector[39] <<24)
        # Offset 44 (0x2C) is the first cluster of the root directory
        first_root_cluster = sector[44] + (sector[45] <<8) + (sector[46] <<16) + (sector[47] <<24)
        # Offset 510 is the signature and we already checked that
        print(bytes_per_sector," bytes per sector")
        print(sectors_per_cluster, " sectors per cluster")
        print(num_reserved_sectors, " reserved sectors")
        print(sectors_per_FAT, " sectors per FAT")
        print(first_root_cluster, " is the first root cluster")
        # Let's bail if the numbers don't make sense.
        if bytes_per_sector != 512:
            sofarsogood = False
            print("The bytes per sector MUST be 512!")
        valid_values = [1, 2, 4, 8, 16, 32, 64, 128]
        try:
            i = valid_values.index(sectors_per_cluster)
        except:
            sofarsogood = False
            print("We can't have ",sectors_per_cluster," sectors per cluster!")
        if num_of_FATs != 2:
            sofarsogood = False
            print("We have to have two FATs")
    if sofarsogood:            
        showfiles = True
        while showfiles:
            cluster_list=[]
            position_list=[]
            
            searchtext = input("What text should I look for? (just Enter to quit) ")
            max_text_spots = input("What is the max number of instances of this bit of text that our code should locate before moving on to stage 2?")
            max_text_spots = int(max_text_spots)
            current_text_spots=0
            # The text could span over a cluster boundary, so let's read in two
            # into a single string and search that. If we find it, we know what cluster
            # it started in.
            for c in range(2, 2 + (128 * sectors_per_FAT) - 1):
                
                # print("Checking clusters",c,",",c+1)
                read_a_cluster(c)  # This is the first one
                s = ""

                for i in range(0, sector_size * sectors_per_cluster):
                    s = s + chr(cluster[i])
                read_a_cluster(c+1)  # This is the second one
                for i in range(0, sector_size * sectors_per_cluster):
                    s = s + chr(cluster[i])
                p = s.find(searchtext)
                if p >= 0 and p < sector_size * sectors_per_cluster:
                    # p is relative to the string of two clusters.
                    # Only report if the string starts in the first cluster
                    print("Found at position ",p, " of cluster ",c)
                    current_text_spots=current_text_spots+1
                    cluster_list.append(int(c))
                    position_list.append(int(p))
                if(current_text_spots >= max_text_spots):
                    break

            # entry_list = []
            
            for count1, cluster_elem in enumerate(cluster_list):
                clustnum = 0
                position_num = 0
                max_text_search_buffer = 35
                characters_read_aloud = 0

                r_endpoint = 0

                # print('for debug purposes to check why certain passwords arent displaying-- printing characters_read_aloud: '+str(characters_read_aloud))

                
                # direct input if needed (currently commented out):
                # max_text_search_buffer = input("Enter the max number of characters at each discovered text location you want read out: ")

                # print("Valid cluster numbers are from 2 to",128*sectors_per_FAT)
                # clustnum = input("Cluster number or a range xx-xx (just Enter to quit) ")
                
                # print('Choose a position between 0 and '+str((bytes_per_sector*sectors_per_cluster)))
                # position_num = input("Enter the approximate position within the cluster")

                
                position_num=int(position_list[count1])
                clustnum=str(cluster_elem)
                print('this is the position of text item ' + str(count1) + ': ' + str(position_num))
                print('this is the cluster of text item ' + str(count1) + ': ' + str(clustnum))

                if len(clustnum) == 0:
                    showfiles = False
                    break
                if clustnum.find("-") < 0:
                    start = int(clustnum)
                    stop = start
                else:
                    start = int(clustnum[:clustnum.find("-")])
                    stop = int(clustnum[1+clustnum.find("-"):])
                if start < 2 or stop > 128*sectors_per_FAT:
                    showfiles = False
                if showfiles:
                    chars_this_line = 0;
                    cluster = []
                    for c in range(start, stop+1):
                        if(characters_read_aloud >= max_text_search_buffer):
                            characters_read_aloud = 0
                            break
                        read_a_cluster(c)
                        r_endpoint=int( (sectors_per_cluster*bytes_per_sector) + position_num )
                        if(r_endpoint >= int( (sectors_per_cluster*bytes_per_sector) )):
                            r_endpoint = int( (sectors_per_cluster*bytes_per_sector) )
                        else:
                            r_endpoint = int( (sectors_per_cluster*bytes_per_sector) + position_num )
                        for b in range((0 + position_num), (r_endpoint)):
                            if cluster[b] >= 32 and cluster[b] <=127:
                                print(chr(cluster[b]), end="")
                                chars_this_line = chars_this_line + 1
                                characters_read_aloud = characters_read_aloud + 1
                                # print('debugging-- char count = '+str(characters_read_aloud))
                                if chars_this_line == 80:
                                      print("")
                                      chars_this_line = 0
                                if(characters_read_aloud >= max_text_search_buffer):
                                    break
                    print("")
                    p_reply = input('Would you like to restore a deleted file (yes/no)?')
                    if (p_reply.upper() == 'YES'):
                        print('ok just remember the cluster of the file you wish to restore and enter the entry number associated with this file when prompted to do so')
                        showfiles = False
                        





 











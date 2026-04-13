# import snap7
# import logging
# from contextlib import contextmanager
# from snap7 import util
# import time

# logger = logging.getLogger(__name__)


# def plc_connect(ip: str, rack: int = 0, slot: int = 2, timeout: int = 5) -> bool:
#     """
#     Check if PLC is reachable and connectable
    
#     Args:
#         ip: PLC IP address
#         rack: Rack number (usually 0)
#         slot: Slot number (2 for S7-300, 1 for S7-1200/1500)
#         timeout: Connection timeout in seconds
    
#     Returns:
#         True if connection successful, False otherwise
#     """
#     client = None
#     try:
#         client = snap7.client.Client()
#         # Don't set timeout - use default
        
#         logger.debug(f"Testing PLC connection to {ip}...")
#         client.connect(ip, rack, slot)
        
#         if client.get_connected():
#             logger.debug(f"✓ PLC at {ip} is reachable")
#             return True
#         else:
#             logger.warning(f"✗ PLC at {ip} connection failed")
#             return False
    
#     except Exception as e:
#         logger.warning(f"✗ Cannot connect to PLC at {ip}: {e}")
#         return False
    
#     finally:
#         if client is not None:
#             try:
#                 if client.get_connected():
#                     client.disconnect()
#             except:
#                 pass


# @contextmanager
# def plc_connection(ip: str, rack: int = 0, slot: int = 2, timeout: int = 5):
#     """
#     Context manager for Snap7 PLC connections
#     Ensures connection is always closed properly
    
#     Usage:
#         with plc_connection('192.168.1.100') as client:
#             db = client.db_read(7, 0, 2)
#             value = util.get_int(db, 0)
#     """
#     client = snap7.client.Client()
#     # Don't set timeout - use default
    
#     try:
#         logger.debug(f"Connecting to PLC at {ip} (Rack {rack}, Slot {slot})")
#         client.connect(ip, rack, slot)
        
#         if not client.get_connected():
#             raise ConnectionError(f"Failed to connect to {ip}")
        
#         logger.debug(f"✓ Connected to PLC at {ip}")
#         yield client
    
#     except Exception as e:
#         logger.error(f"PLC connection error for {ip}: {e}")
#         raise
    
#     finally:
#         try:
#             if client.get_connected():
#                 client.disconnect()
#                 logger.debug(f"✓ Disconnected from PLC {ip}")
#         except Exception as e:
#             logger.warning(f"Error during disconnect from {ip}: {e}")


# def read_value(ip: str, db_name: int, offset: int, field_type: str = 'int', 
#                rack: int = 0, slot: int = 2, timeout: int = 5):
#     """
#     Read value from PLC with proper connection management
    
#     Args:
#         ip: PLC IP address
#         db_name: Data block number (e.g., 7 for DB7)
#         offset: Start address in bytes (e.g., 182 for DBW182)
#         field_type: 'int' (2 bytes) or 'dint' (4 bytes)
#         rack: Rack number (usually 0)
#         slot: Slot number (2 for S7-300, 1 for S7-1200/1500)
#         timeout: Connection timeout in seconds (not used, kept for compatibility)
    
#     Returns:
#         Value read from PLC, or -1 on error
#     """
#     try:
#         # Check initial connection
#         if not plc_connect(ip, rack, slot, timeout):
#             logger.warning(f"PLC connection check failed for {ip}")
#             return -1
        
#         # Use context manager for connection
#         with plc_connection(ip, rack=rack, slot=slot, timeout=timeout) as client:
#             byte_num = 2 if field_type == 'int' else 4
            
#             # Read from database
#             db = client.db_read(db_name, offset, byte_num)
            
#             # Parse value based on type
#             if byte_num == 2:
#                 value = util.get_int(db, 0)      # 2-byte integer
#             else:
#                 value = util.get_dint(db, 0)     # 4-byte integer
            
#             logger.debug(f"✓ Read from {ip}:DB{db_name}.DBW{offset} = {value}")
#             return value
    
#     except Exception as e:
#         logger.error(f"Failed to read value from {ip}: {e}")
#         return -1


# def read_multiple_values(ip: str, reads: list, rack: int = 0, slot: int = 2, timeout: int = 5):
#     """
#     Read multiple values from PLC in a single connection (more efficient)
    
#     Args:
#         ip: PLC IP address
#         reads: List of tuples (db_name, offset, field_type, label)
#                Example: [(7, 182, 'int', 'Crane Hours'), (7, 184, 'dint', 'Count')]
#         rack: Rack number
#         slot: Slot number
#         timeout: Connection timeout (not used, kept for compatibility)
    
#     Returns:
#         Dictionary with labels as keys and values
#     """
#     results = {}
    
#     try:
#         if not plc_connect(ip, rack, slot, timeout):
#             logger.warning(f"PLC connection check failed for {ip}")
#             return results
        
#         with plc_connection(ip, rack=rack, slot=slot, timeout=timeout) as client:
#             for db_name, offset, field_type, label in reads:
#                 try:
#                     byte_num = 2 if field_type == 'int' else 4
#                     db = client.db_read(db_name, offset, byte_num)
                    
#                     if byte_num == 2:
#                         value = util.get_int(db, 0)
#                     else:
#                         value = util.get_dint(db, 0)
                    
#                     results[label] = value
#                     logger.debug(f"✓ {label}: {value}")
                
#                 except Exception as e:
#                     logger.error(f"Error reading {label}: {e}")
#                     results[label] = -1
    
#     except Exception as e:
#         logger.error(f"Failed to read multiple values from {ip}: {e}")
    
#     return results

import snap7
import logging
from contextlib import contextmanager
from snap7 import util
import socket
import time

logger = logging.getLogger(__name__)


def ping_plc(ip: str, timeout: int = 2) -> bool:
    """
    Check if PLC is reachable via ICMP ping
    
    Args:
        ip: PLC IP address
        timeout: Timeout in seconds
    
    Returns:
        True if ping successful, False otherwise
    """
    try:
        # Use socket to simulate ping
        sock = socket.create_connection((ip, 102), timeout=timeout)
        sock.close()
        logger.debug(f"✓ Ping successful to {ip}")
        return True
    except socket.timeout:
        logger.warning(f"✗ Ping timeout to {ip}")
        return False
    except socket.error as e:
        logger.warning(f"✗ Ping failed to {ip}: {e}")
        return False


def plc_connect(ip: str, rack: int = 0, slot: int = 2, timeout: int = 5) -> dict:
    """
    Check if PLC is connectable and return detailed status
    
    Returns:
        {
            'connected': bool,
            'ping_ok': bool,
            'snap7_ok': bool,
            'error': str,
            'status': 'ping_only' | 'snap7_ok' | 'error'
        }
    """
    result = {
        'connected': False,
        'ping_ok': False,
        'snap7_ok': False,
        'error': None,
        'status': 'error'
    }
    
    # Step 1: Check ping
    logger.info(f"Step 1: Checking ping to {ip}...")
    result['ping_ok'] = ping_plc(ip, timeout)
    
    if not result['ping_ok']:
        result['error'] = 'Ping failed - PLC unreachable'
        result['status'] = 'error'
        logger.error(f"❌ {result['error']}")
        return result
    
    logger.info(f"✓ Ping OK")
    
    # Step 2: Check Snap7 connection
    client = None
    try:
        logger.info(f"Step 2: Checking Snap7 connection (Rack {rack}, Slot {slot})...")
        client = snap7.client.Client()
        client.connect(ip, rack, slot)
        
        if client.get_connected():
            logger.info(f"✓ Snap7 connected")
            result['snap7_ok'] = True
            result['connected'] = True
            result['status'] = 'snap7_ok'
            return result
        else:
            result['error'] = 'Snap7 connection failed (not connected)'
            result['status'] = 'ping_only'
            logger.warning(f"⚠️  {result['error']}")
            return result
    
    except Exception as e:
        error_msg = str(e)
        result['error'] = f'Snap7 connection error: {error_msg}'
        
        # Classify the error
        if 'unreachable' in error_msg.lower():
            result['status'] = 'ping_only'
            logger.warning(f"⚠️  PLC reachable (ping OK) but Snap7 connection failed")
            logger.warning(f"   Possible causes:")
            logger.warning(f"   - Snap7 service not running on PLC")
            logger.warning(f"   - TCP port 102 blocked by firewall")
            logger.warning(f"   - Wrong Rack/Slot setting")
        elif 'timeout' in error_msg.lower():
            result['status'] = 'timeout'
            logger.warning(f"⚠️  Snap7 connection timeout")
            logger.warning(f"   Possible causes:")
            logger.warning(f"   - Network congestion")
            logger.warning(f"   - PLC too busy")
        else:
            logger.error(f"❌ {result['error']}")
        
        return result
    
    finally:
        if client is not None:
            try:
                if client.get_connected():
                    client.disconnect()
            except:
                pass


@contextmanager
def plc_connection(ip: str, rack: int = 0, slot: int = 2, timeout: int = 5):
    """
    Context manager for Snap7 PLC connections
    """
    client = snap7.client.Client()
    
    try:
        logger.debug(f"Connecting to PLC at {ip} (Rack {rack}, Slot {slot})")
        client.connect(ip, rack, slot)
        
        if not client.get_connected():
            raise ConnectionError(f"Failed to connect to {ip}")
        
        logger.debug(f"✓ Connected to PLC at {ip}")
        yield client
    
    except Exception as e:
        logger.error(f"PLC connection error for {ip}: {e}")
        raise
    
    finally:
        try:
            if client.get_connected():
                client.disconnect()
                logger.debug(f"✓ Disconnected from PLC {ip}")
        except Exception as e:
            logger.warning(f"Error during disconnect from {ip}: {e}")


def read_value(ip: str, db_name: int, offset: int, field_type: str = 'int', 
               rack: int = 0, slot: int = 2, timeout: int = 5):
    """
    Read value from PLC with enhanced error detection
    """
    try:
        # Check connection status first
        status = plc_connect(ip, rack, slot, timeout)
        
        if status['status'] == 'ping_only':
            # PLC responds to ping but Snap7 fails
            logger.error(f"❌ PLC ping OK but Snap7 failed: {status['error']}")
            return -1
        
        if not status['connected']:
            logger.error(f"❌ PLC connection check failed: {status['error']}")
            return -1
        
        # Connection OK, proceed with read
        with plc_connection(ip, rack=rack, slot=slot, timeout=timeout) as client:
            byte_num = 2 if field_type == 'int' else 4
            db = client.db_read(db_name, offset, byte_num)
            
            if byte_num == 2:
                value = util.get_int(db, 0)
            else:
                value = util.get_dint(db, 0)
            
            logger.debug(f"✓ Read from {ip}:DB{db_name}.DBW{offset} = {value}")
            return value
    
    except Exception as e:
        logger.error(f"Failed to read value from {ip}: {e}")
        return -1


def read_multiple_values(ip: str, reads: list, rack: int = 0, slot: int = 2, timeout: int = 5):
    """
    Read multiple values from PLC with enhanced error detection
    """
    results = {}
    
    try:
        # Check connection status first
        status = plc_connect(ip, rack, slot, timeout)
        
        if status['status'] == 'ping_only':
            # PLC responds to ping but Snap7 fails
            logger.error(f"❌ PLC ping OK but Snap7 failed: {status['error']}")
            for _, _, _, label in reads:
                results[label] = -1
            return results
        
        if not status['connected']:
            logger.error(f"❌ PLC connection check failed: {status['error']}")
            for _, _, _, label in reads:
                results[label] = -1
            return results
        
        # Connection OK, proceed with reads
        with plc_connection(ip, rack=rack, slot=slot, timeout=timeout) as client:
            for db_name, offset, field_type, label in reads:
                try:
                    byte_num = 2 if field_type == 'int' else 4
                    db = client.db_read(db_name, offset, byte_num)
                    
                    if byte_num == 2:
                        value = util.get_int(db, 0)
                    else:
                        value = util.get_dint(db, 0)
                    
                    results[label] = value
                    logger.debug(f"✓ {label}: {value}")
                
                except Exception as e:
                    logger.error(f"Error reading {label}: {e}")
                    results[label] = -1
    
    except Exception as e:
        logger.error(f"Failed to read multiple values from {ip}: {e}")
        for _, _, _, label in reads:
            results[label] = -1
    
    return results
package com.microsoft.frameworklauncher.common.utils;

import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * @author christopher
 * @since 10/15/18
 */
public class CompressionUtilsTest {

    private static final byte[] UNCOMPRESSED_BYTES = "uncompressed input".getBytes();

    @Test
    public void compress() throws Exception {
        final byte[] compressedBytes = CompressionUtils.compress(UNCOMPRESSED_BYTES);
        assertTrue(CompressionUtils.isCompressed(compressedBytes));
    }

    @Test
    public void decompress() throws Exception {
        final byte[] compressedBytes = CompressionUtils.compress(UNCOMPRESSED_BYTES);
        final byte[] decompressedBytes = CompressionUtils.decompress(compressedBytes);
        assertFalse(CompressionUtils.isCompressed(decompressedBytes));
    }

}
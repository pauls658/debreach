/* minigzip.c -- simulate gzip using the zlib compression library
 * Copyright (C) 1995-2006, 2010, 2011 Jean-loup Gailly.
 * For conditions of distribution and use, see copyright notice in zlib.h
 */

/*
 * minigzip is a minimal implementation of the gzip utility. This is
 * only an example of using zlib and isn't meant to replace the
 * full-featured gzip. No attempt is made to deal with file systems
 * limiting names to 14 or 8+3 characters, etc... Error checking is
 * very limited. So use minigzip only for testing; use gzip for the
 * real thing. On MSDOS, use only on file names without extension
 * or in pipe mode.
 */

/* @(#) $Id$ */

#include "zlib.h"
#include <stdio.h>

#ifdef STDC
#  include <string.h>
#  include <stdlib.h>
#endif

#if defined(MSDOS) || defined(OS2) || defined(WIN32) || defined(__CYGWIN__)
#  include <fcntl.h>
#  include <io.h>
#  ifdef UNDER_CE
#    include <stdlib.h>
#  endif
#  define SET_BINARY_MODE(file) setmode(fileno(file), O_BINARY)
#else
#  define SET_BINARY_MODE(file)
#endif

#ifdef _MSC_VER
#  define snprintf _snprintf
#endif

#ifdef VMS
#  define unlink delete
#  define GZ_SUFFIX "-gz"
#endif
#ifdef RISCOS
#  define unlink remove
#  define GZ_SUFFIX "-gz"
#  define fileno(file) file->__file
#endif
#if defined(__MWERKS__) && __dest_os != __be_os && __dest_os != __win32_os
#  include <unix.h> /* for fileno */
#endif

#if !defined(Z_HAVE_UNISTD_H) && !defined(_LARGEFILE64_SOURCE)
#ifndef WIN32 /* unlink already in stdio.h for WIN32 */
  extern int unlink OF((const char *));
#endif
#endif

#if defined(UNDER_CE)
#  include <windows.h>
#  define perror(s) pwinerror(s)

/* Map the Windows error number in ERROR to a locale-dependent error
   message string and return a pointer to it.  Typically, the values
   for ERROR come from GetLastError.

   The string pointed to shall not be modified by the application,
   but may be overwritten by a subsequent call to strwinerror

   The strwinerror function does not change the current setting
   of GetLastError.  */

static char *strwinerror (error)
     DWORD error;
{
    static char buf[1024];

    wchar_t *msgbuf;
    DWORD lasterr = GetLastError();
    DWORD chars = FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM
        | FORMAT_MESSAGE_ALLOCATE_BUFFER,
        NULL,
        error,
        0, /* Default language */
        (LPVOID)&msgbuf,
        0,
        NULL);
    if (chars != 0) {
        /* If there is an \r\n appended, zap it.  */
        if (chars >= 2
            && msgbuf[chars - 2] == '\r' && msgbuf[chars - 1] == '\n') {
            chars -= 2;
            msgbuf[chars] = 0;
        }

        if (chars > sizeof (buf) - 1) {
            chars = sizeof (buf) - 1;
            msgbuf[chars] = 0;
        }

        wcstombs(buf, msgbuf, chars + 1);
        LocalFree(msgbuf);
    }
    else {
        sprintf(buf, "unknown win32 error (%ld)", error);
    }

    SetLastError(lasterr);
    return buf;
}

static void pwinerror (s)
    const char *s;
{
    if (s && *s)
        fprintf(stderr, "%s: %s\n", s, strwinerror(GetLastError ()));
    else
        fprintf(stderr, "%s\n", strwinerror(GetLastError ()));
}

#endif /* UNDER_CE */

#ifndef GZ_SUFFIX
#  define GZ_SUFFIX ".gz"
#endif
#define SUFFIX_LEN (sizeof(GZ_SUFFIX)-1)

#define BUFLEN      16384
#define MAX_NAME_LEN 1024

#ifdef MAXSEG_64K
#  define local static
   /* Needed for systems with limitation on stack size. */
#else
#  define local
#endif

/* for Z_SOLO, create simplified gz* functions using deflate and inflate */

#if defined(Z_HAVE_UNISTD_H) || defined(Z_LARGE)
#  include <unistd.h>       /* for unlink() */
#endif

void *myalloc OF((void *, unsigned, unsigned));
void myfree OF((void *, void *));

void *myalloc(q, n, m)
    void *q;
    unsigned n, m;
{
    q = Z_NULL;
    return calloc(n, m);
}

void myfree(q, p)
    void *q, *p;
{
    q = Z_NULL;
    free(p);
}

typedef struct gzFile_st {
    FILE *file;
    int write;
    int err;
    char *msg;
    z_stream strm;
} *gzFilet;

gzFilet gzopent OF((const char *, const char *));
gzFilet gzdopent OF((int, const char *));
gzFilet gz_opent OF((const char *, int, const char *));

gzFilet gzopent(path, mode)
const char *path;
const char *mode;
{
    return gz_opent(path, -1, mode);
}

gzFilet gzdopent(fd, mode)
int fd;
const char *mode;
{
    return gz_opent(NULL, fd, mode);
}

gzFilet gz_opent(path, fd, mode)
    const char *path;
    int fd;
    const char *mode;
{
    gzFilet gz;
    int ret;

    gz = malloc(sizeof(struct gzFile_st));
    if (gz == NULL)
        return NULL;
    gz->write = strchr(mode, 'w') != NULL;
    gz->strm.zalloc = myalloc;
    gz->strm.zfree = myfree;
    gz->strm.opaque = Z_NULL;
    if (gz->write)
        ret = deflateInit2(&(gz->strm), -1, 8, 15 + 16, 8, 0);
    else {
        gz->strm.next_in = 0;
        gz->strm.avail_in = Z_NULL;
        ret = inflateInit2(&(gz->strm), 15 + 16);
    }
    if (ret != Z_OK) {
        free(gz);
        return NULL;
    }
    gz->file = path == NULL ? fdopen(fd, gz->write ? "wb" : "rb") :
                              fopen(path, gz->write ? "wb" : "rb");
    if (gz->file == NULL) {
        gz->write ? deflateEnd(&(gz->strm)) : inflateEnd(&(gz->strm));
        free(gz);
        return NULL;
    }
    gz->err = 0;
    gz->msg = "";
    return gz;
}

int gzreadt OF((gzFilet, void *, unsigned));

int gzreadt(gz, buf, len)
    gzFilet gz;
    void *buf;
    unsigned len;
{
    int ret;
    unsigned got;
    unsigned char in[1];
    z_stream *strm;

    if (gz == NULL || gz->write)
        return 0;
    if (gz->err)
        return 0;
    strm = &(gz->strm);
    strm->next_out = (void *)buf;
    strm->avail_out = len;
    do {
        got = fread(in, 1, 1, gz->file);
        if (got == 0)
            break;
        strm->next_in = in;
        strm->avail_in = 1;
        ret = inflate(strm, Z_NO_FLUSH);
        if (ret == Z_DATA_ERROR) {
            gz->err = Z_DATA_ERROR;
            gz->msg = strm->msg;
            return 0;
        }
        if (ret == Z_STREAM_END)
            inflateReset(strm);
    } while (strm->avail_out);
    return len - strm->avail_out;
}

const char *gzerrort OF((gzFilet, int *));

const char *gzerrort(gz, err)
    gzFilet gz;
    int *err;
{
    *err = gz->err;
    return gz->msg;
}


char *prog;

void error            OF((const char *msg));
void gz_compress      OF((FILE   *in, gzFilet out, char **unsafe));
void gz_uncompress    OF((gzFilet in, FILE   *out));
void file_compress    OF((char  *file, char *mode, char **unsafe));
void file_uncompress  OF((char  *file));
int gzwritet OF((gzFilet, const void *, unsigned, char **));
int gzcloset OF((gzFilet, char **));
int  main             OF((int argc, char *argv[]));

/* Should be called printTaintArray because it expects the
 * double 0 terminator */
void printIntArray(arr, out) 
    unsigned int *arr;
	FILE *out;
{
    unsigned int *temp = arr;
	if (arr == NULL || (temp[0] == 0 && temp[1] == 0)) {
    	fprintf(out, "\n");
		return;
	}
	fprintf(out, "%u", *temp);
	temp++;
    while (!(temp[0] == 0 && temp[1] == 0)) {
      fprintf(out, " %u", *temp);
      temp++;
    }
    fprintf(out, "\n");
}

/* ===========================================================================
 * Display error message and exit
 */
void error(msg)
    const char *msg;
{
    fprintf(stderr, "%s: %s\n", prog, msg);
    exit(1);
}

/* Helper function */
unsigned int u_max(unsigned int a, unsigned int b) {
	return a > b ? a : b;
}

unsigned int* get_byte_ranges(const char *buf, unsigned int buf_len, char **unsafe) {
	if (unsafe == NULL) {
		fprintf(stdout, "unsafe was null. wat\n");
		return NULL;
	}
	int array_size = 20;
	unsigned int *brs = (unsigned int*) malloc(sizeof(int)*array_size);
	// TODO: alloc error handling
	unsigned int buf_i = 0, br_i = 0;
	char **temp;
	// Special case: buf begins with partial unsafe string
	unsigned int match_len = 0;
	short match;
	char *unsafe_str;
	unsigned unsafe_pos = 0;
	// Find the longest match of any substring of the unsafe strings at the beginning of the
	// buf
	for (temp = unsafe; *temp != NULL; temp++) {
		unsafe_str = *temp;
		// check all substrings
		while (*unsafe_str != '\0') {
			match = 1;
			unsafe_pos = 0;
			while(unsafe_str[unsafe_pos] != '\0' && unsafe_pos < buf_len) {
				if (unsafe_str[unsafe_pos] != buf[unsafe_pos]) {
					match = 0;
					break;
				}
				unsafe_pos++;
			}
			if (match) {
				//fprintf(stderr, "match found out beginning: ");
				//fwrite(buf, 1, unsafe_pos + 1, stderr);
				//fprintf(stderr, "\n");
				// unsafe_pos is at the index just after the end of the
				// string
				match_len = u_max(match_len, unsafe_pos);
				// we can stop checking substrings of this string
				// breaking here goes to the next unsafe string
				break;
			}
			unsafe_str++;
		}
	}

	// match_len is only updated if we found a match in the previous loop
	// therefore match_len == 0 if there were no matches found
	if (match_len > 0) {
		brs[0] = 0;
		brs[1] = match_len - 1;
		//fprintf(stderr, "Making byte range: %d - %d\n", brs[0], brs[1]);
		buf_i += match_len;
		br_i += 2;
	}

	while (buf_i < buf_len) {
		// check if any of the unsafe strings appear at buf_i
		for (temp = unsafe; *temp != NULL; temp++) {
			unsafe_str = *temp;
			match = 1;
			match_len = 0;
			// Check if any unsafe strings appear at buf_i. Also make sure we don't go
			// out of the buffer
			while (unsafe_str[match_len] != '\0' && buf_i + match_len < buf_len) {
				if (unsafe_str[match_len] != buf[buf_i + match_len]) {
					match = 0;
					break;
				}
				match_len++;
			}
			if (match == 1 && match_len > 0) {
				//fprintf(stderr, "match: %s\n", unsafe_str);
				//fprintf(stderr, "buf_i: %u, brs[br_i + 1]: %u\n", buf_i, brs[br_i + 1]);
				// Either we reached the end of an unsafe string, or we reached the end of the
				// buffer. In both cases, add the byte range
				
				// Make a new byte range
				// realloc if we have to
				// br_i + 4 is the size of what we need
				// - 2 from array_size because we need 2 spaces for terminator
				if (br_i + 4 > array_size - 2) {
					array_size = 2*array_size;
					brs = (unsigned int*) realloc(brs, array_size*sizeof(unsigned int));
				}
				// TODO: alloc error handling
				brs[br_i] = buf_i;
				brs[br_i + 1] = buf_i + match_len - 1;
				br_i += 2;
				// - 1 here becasue we always increment by 1 at the end of the main loop
				buf_i += match_len - 1;
				break;
			}
		}
		buf_i += 1;
	}
	if (br_i == 0) {
		return NULL;
	} else {
		brs[br_i] = 0;
		brs[br_i + 1] = 0;
		return brs;
	}
}

int gzwritet(gz, buf, len, unsafe)
    gzFilet gz;
    const void *buf;
    unsigned len;
	char **unsafe;
{
    z_stream *strm;
    unsigned char out[BUFLEN];
	unsigned int *brs = get_byte_ranges((char*)buf, len, unsafe);
	int ret;
#ifdef BRS_ONLY
	fprintf(stdout, "byteranges: ");
	printIntArray(brs, stdout);
	fwrite(buf, 1, len, stdout);
	printf("\n");
	return len;
#endif
    if (gz == NULL || !gz->write)
        return 0;

    strm = &(gz->strm);
    strm->next_in = (void *)buf;
	// The next input byte in the buffer
	unsigned buf_pos = 0;

	// Special case: beginning of buffer is tainted
	if (brs != NULL && brs[0] == 0 && brs[1] != 0) {
		strm->next_out = out;
        strm->avail_out = BUFLEN;
		ret = deflateParams(strm, Z_NO_COMPRESSION, Z_DEFAULT_STRATEGY);
		strm->avail_in = brs[1] + 1;
		buf_pos += strm->avail_in;
		do {
            strm->next_out = out;
            strm->avail_out = BUFLEN;
    		(void)deflate(strm, Z_FULL_FLUSH);
            fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
    		// strm->avail_out == 0 means that there is more output to be written
        } while (strm->avail_out == 0);
		if (buf_pos == len) {
			return len;
		} else if (buf_pos > len) {
			fprintf(stderr, "Warning: buf_pos > len doing stored block at beginning of buf. The index in the buffer should not be greater than the length of the buffer itself. Possible buffer overflow.\n");
		}
		brs += 2;
	}

	for (;;) {
        strm->next_out = out;
        strm->avail_out = BUFLEN;
		ret = deflateParams(strm, -1, Z_DEFAULT_STRATEGY);
        fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
		if (brs == NULL || (brs[0] == 0 && brs[1] == 0)) {
			// no more taint left. Finish it off
			strm->avail_in = len - buf_pos;
		} else {
			strm->avail_in = brs[0] - buf_pos;
		}
		buf_pos += strm->avail_in;
		// next_in is updated automatically
        do {
            strm->next_out = out;
            strm->avail_out = BUFLEN;
    		(void)deflate(strm, Z_NO_FLUSH);
            fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
    		// strm->avail_out == 0 means that our output buffer filled up, so we need to call deflate again
			// in case there is more output
        } while (strm->avail_out == 0);
		// if there is no more input, we are done, and there is no need to flush
		if (buf_pos == len) {
			break;
		} else if (buf_pos > len) {
			fprintf(stderr, "Warning: buf_pos > len after doing the compressed block. The index in the buffer should not be greater than the length of the buffer itself. Possible buffer overflow\n");
		}
		// Change the compression method
        strm->next_out = out;
        strm->avail_out = BUFLEN;
		ret = deflateParams(strm, Z_NO_COMPRESSION, Z_DEFAULT_STRATEGY);
        fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
		// buf_pos should == brs[0]
		strm->avail_in = brs[1] - buf_pos + 1;
		buf_pos += strm->avail_in;
		if (ret != Z_OK) {
			fprintf(stderr, "deflateParams() had a bad return value.\n");
		}
		// just force the flush from the get go
		do {
            strm->next_out = out;
            strm->avail_out = BUFLEN;
    		(void)deflate(strm, Z_FULL_FLUSH);
            fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
    		// strm->avail_out == 0 means that there is more output to be written
        } while (strm->avail_out == 0);
		// Check to see if we are done
		if (buf_pos == len) {
			break;
		} else if (buf_pos > len) {
			fprintf(stderr, "Warning: buf_pos > len after doing the stored block. The index in the buffer should not be greater than the length of the buffer itself. Possible buffer overflow.\n");
		}
		if (!(brs[0] == 0 && brs[1] == 0))
			brs += 2;
	}
    return len;
}

int gzcloset(gz, unsafe)
    gzFilet gz;
	char **unsafe;
{
    z_stream *strm;
    unsigned char out[BUFLEN];

    if (gz == NULL)
        return Z_STREAM_ERROR;
    strm = &(gz->strm);
    if (gz->write) {
        strm->next_in = Z_NULL;
        strm->avail_in = 0;
        do {
            strm->next_out = out;
            strm->avail_out = BUFLEN;
            (void)deflate(strm, Z_FINISH);
            fwrite(out, 1, BUFLEN - strm->avail_out, gz->file);
        } while (strm->avail_out == 0);
        deflateEnd(strm);
    }
    else
        inflateEnd(strm);
    fclose(gz->file);
    free(gz);
    return Z_OK;
}

/* ===========================================================================
 * Compress input to output then close both files.
 */

void gz_compress(in, out, unsafe)
    FILE   *in;
    gzFilet out;
	char **unsafe;
{
    local char buf[BUFLEN];
    int len;
    int err;

    for (;;) {
        len = (int)fread(buf, 1, sizeof(buf), in);
        if (ferror(in)) {
            perror("fread");
            exit(1);
        }
        if (len == 0) break;

        if (gzwritet(out, buf, (unsigned)len, unsafe) != len) error(gzerrort(out, &err));
    }
    fclose(in);
    if (gzcloset(out, unsafe) != Z_OK) error("failed gzclose");
}


/* ===========================================================================
 * Uncompress input to output then close both files.
 */
void gz_uncompress(in, out)
    gzFilet in;
    FILE   *out;
{
    local char buf[BUFLEN];
    int len;
    int err;

    for (;;) {
        len = gzreadt(in, buf, sizeof(buf));
        if (len < 0) error (gzerrort(in, &err));
        if (len == 0) break;

        if ((int)fwrite(buf, 1, (unsigned)len, out) != len) {
            error("failed fwrite");
        }
    }
    if (fclose(out)) error("failed fclose");

	// Don't need debreach for uncompress
	// use regular zlib
    if (gzcloset(in, NULL) != Z_OK) error("failed gzclose");
}


/* ===========================================================================
 * Compress the given file: create a corresponding .gz file and remove the
 * original.
 */
void file_compress(file, mode, unsafe)
    char  *file;
    char  *mode;
	char **unsafe;
{
    local char outfile[MAX_NAME_LEN];
    FILE  *in;
    gzFilet out;

    if (strlen(file) + strlen(GZ_SUFFIX) >= sizeof(outfile)) {
        fprintf(stderr, "%s: filename too long\n", prog);
        exit(1);
    }

#if !defined(NO_snprintf) && !defined(NO_vsnprintf)
    snprintf(outfile, sizeof(outfile), "%s%s", file, GZ_SUFFIX);
#else
    strcpy(outfile, file);
    strcat(outfile, GZ_SUFFIX);
#endif

    in = fopen(file, "rb");
    if (in == NULL) {
        perror(file);
        exit(1);
    }
    out = gzopent(outfile, mode);
    if (out == NULL) {
        fprintf(stderr, "%s: can't gzopent %s\n", prog, outfile);
        exit(1);
    }
    gz_compress(in, out, unsafe);

}


/* ===========================================================================
 * Uncompress the given file and remove the original.
 */
void file_uncompress(file)
    char  *file;
{
    local char buf[MAX_NAME_LEN];
    char *infile, *outfile;
    FILE  *out;
    gzFilet in;
    size_t len = strlen(file);

    if (len + strlen(GZ_SUFFIX) >= sizeof(buf)) {
        fprintf(stderr, "%s: filename too long\n", prog);
        exit(1);
    }

#if !defined(NO_snprintf) && !defined(NO_vsnprintf)
    snprintf(buf, sizeof(buf), "%s", file);
#else
    strcpy(buf, file);
#endif

    if (len > SUFFIX_LEN && strcmp(file+len-SUFFIX_LEN, GZ_SUFFIX) == 0) {
        infile = file;
        outfile = buf;
        outfile[len-3] = '\0';
    } else {
        outfile = file;
        infile = buf;
#if !defined(NO_snprintf) && !defined(NO_vsnprintf)
        snprintf(buf + len, sizeof(buf) - len, "%s", GZ_SUFFIX);
#else
        strcat(infile, GZ_SUFFIX);
#endif
    }
    in = gzopent(infile, "rb");
    if (in == NULL) {
        fprintf(stderr, "%s: can't gzopent %s\n", prog, infile);
        exit(1);
    }
    out = fopen(outfile, "wb");
    if (out == NULL) {
        perror(file);
        exit(1);
    }

    gz_uncompress(in, out);

}


#define MAX_UNSAFE_LEN 1024

/**
 * Returns 1 if every character in the string is a digit, 
 * otherwise returns 0.
 */
int isNumber(str)
    char *str;
{
    char *temp = str;
    while (*temp != '\0') {
      if (isdigit((int)*temp) == 0)
	return 0;
      temp++;
    }
    return 1;
}

/**
* Returns the number of occurences of the given char in the string.
*/
int charCount(str, c)
   char *str;
   char c;
{
   int ct = 0;
   char *temp = str;
   while (*temp != '\0') {
	   if (*temp == c)
		   ct++;
	   temp++;
   }
   return ct;
}

/* ===========================================================================
 * Usage:  minigzip [-c] [-d] [-f] [-h] [-r] [-1 to -9] [files...]
 *   -c : write to standard output
 *   -d : decompress
 *   -f : compress with Z_FILTERED
 *   -h : compress with Z_HUFFMAN_ONLY
 *   -r : compress with Z_RLE
 *   -1 to -9 : compression level
 *   -s <string>[,<string>]... : a list of strings that we don't want to compress
 */

int main(argc, argv)
    int argc;
    char *argv[];
{
    int copyout = 0;
    int uncompr = 0;
    gzFilet file;
    char *bname, outmode[20];
	char **unsafe = NULL;
	unsigned int *taint = NULL;

#if !defined(NO_snprintf) && !defined(NO_vsnprintf)
    snprintf(outmode, sizeof(outmode), "%s", "wb6 ");
#else
    strcpy(outmode, "wb6 ");
#endif

	int c;
	extern char *optarg;
	while ((c = getopt(argc, argv, "cdfhrl:s:b:")) != -1) {
#ifdef ARGS_DEBUG
		printf("Read arg: -%c\n", c);
#endif
		if (c == 'd') {
			uncompr = 1;
		} else if (c == 'c') {
			copyout = 1;
		} else if (c == 'f') {
			outmode[3] = 'f';
		} else if (c == 'h') {
			outmode[3] = 'f';
		} else if (c == 'r') {
			outmode[3] = 'R';
		} else if (c == 'l') {
			if (isNumber(*optarg)) {
				outmode[2] = *optarg;
			} else {
				printf("Invalid argument for -l: %s\n", optarg);
				exit(1);
			}
		} else if (c == 's') {
			// get the number of strings we need to allocate
			int n = charCount(optarg, ',') + 1;
#ifdef ARGS_DEBUG
			fprintf(stderr, "num strings: %d\n", n);
#endif
			// + 1 for null term
			unsafe = (char **) malloc(sizeof(char *)*(n + 1));
			char *comma, **temp = unsafe;
			int len;
			while (1) {
#ifdef ARGS_DEBUG
				fprintf(stderr, "start\n");
#endif
				comma = strstr(optarg, ",");
				if (comma == NULL) {
#ifdef ARGS_DEBUG
					fprintf(stderr, "read string: %s\n", optarg);
#endif
					len = strnlen(optarg, MAX_UNSAFE_LEN);
					*temp = (char *) malloc(sizeof(char)*(len + 1));
					strncpy(*temp, optarg, len);
					(*temp)[len] = '\0';
#ifdef ARGS_DEBUG
					fprintf(stderr, "unsafe string: %s\n", *temp);
#endif
					temp++;
					break;
				}
				*comma = '\0';
#ifdef ARGS_DEBUG
				fprintf(stderr, "read string: %s\n", optarg);
#endif
				len = strnlen(optarg, MAX_UNSAFE_LEN);
				*temp = (char *) malloc(sizeof(char)*(len + 1));
				strncpy(*temp, optarg, len);
				(*temp)[len] = '\0';
#ifdef ARGS_DEBUG
				fprintf(stderr, "unsafe string: %s\n", *temp);
#endif
				temp++;
				optarg = comma + 1;
			}
			*temp = NULL;
		} else if (c == 'b') {
			// get the number of usnigned ints we need to allocate
			int n = charCount(optarg, ',') + 1;
			if (n % 2 != 0) {
				printf("Invalid argument for -b: odd number of byte values supplied.\n");
				printf("Argument: %s\n", optarg);
				exit(1);
			}
			// + 2 for the double null terminator
			taint = malloc(sizeof(unsigned int)*(n + 2));
			char *temp;
			int i = 0;
			while (1) {
				temp = strstr(optarg, ",");
				if (temp == NULL) {
					if (isNumber(optarg)) {
						taint[i] = atoi(optarg);
						break;
					} else {
						printf("Invalid argument for -b: %s\n", optarg);
						exit(1);
					}
				}
				*temp = '\0';
				if (isNumber(optarg)) {
					taint[i] = atoi(optarg);
					i++;
					optarg = temp + 1;
				} else {
					printf("Invalid argument for -b: %s\n", optarg);
					exit(1);
				}
			}
			taint[n] = 0;
			taint[n + 1] = 0;
		} else {
			printf("Invalid parameter: -%c\n", c);
			exit(1);
		}
	}

    if (outmode[3] == ' ') outmode[3] = 0;

#ifdef ARGS_DEBUG
	printf("Params read in:\n");
	printf("uncompr: %d\n", uncompr);
	printf("copyout: %d\n", copyout);
	printf("outmode[3] (huff, rle, or filter):");
	if (outmode[3] == 0)
		printf(" none\n");
	else
		printf(" %c\n", outmode[3]);
	printf("outmode[2] (compression level): %c\n", outmode[2]);
	if (taint != NULL) {
		printf("taint byte ranges: ");
		printIntArray(taint, stdout);
	}
	if (unsafe != NULL) {
		printf("unsafe strings:\n"); 
		char **temp = unsafe;
		while (*temp != NULL) {
			printf("%s\n", *temp);
			temp++;
		}
	}
#endif

	// Not handling byte ranges yet
	if (taint != NULL) {
		printf("Error: -b not yet implemented\n");
		exit(1);
	}

	if (taint != NULL && unsafe != NULL) {
		printf("Error: -b and -s cannot be used together\n");
		exit(1);
	}

    if (access(argv[argc - 1], R_OK) != 0) {
		printf("Error: could not open %s for reading.\n", argv[argc - 1]);
		exit(1);
    }

    if (copyout) {
        SET_BINARY_MODE(stdout);
    }

    if (uncompr) {
        if (copyout) {
            file = gzopent(argv[argc - 1], "rb");
            if (file == NULL)
                fprintf(stderr, "%s: can't gzopent %s\n", prog, argv[argc - 1]);
            else
                gz_uncompress(file, stdout);
        } else {
            file_uncompress(argv[argc - 1]);
        }
    } else {
        if (copyout) {
            FILE * in = fopen(argv[argc - 1], "rb");

            if (in == NULL) {
                perror(argv[argc - 1]);
            } else {
                file = gzdopent(fileno(stdout), outmode);
                if (file == NULL) error("can't gzdopen stdout");

                gz_compress(in, file, unsafe);
            }

        } else {
            file_compress(argv[argc - 1], outmode, unsafe);
        }
    }
    return 0;
}

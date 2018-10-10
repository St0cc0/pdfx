# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import sys
IS_PY2 = sys.version_info < (3, 0)

import ssl

from collections import defaultdict
from .threadpool import ThreadPool
from .colorprint import colorprint, OKGREEN, FAIL

header = {"User-Agent": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)"}
MAX_THREADS_DEFAULT = 7

# Used to allow downloading files even if https certificate doesn't match
if hasattr(ssl, "_create_unverified_context"):
    ssl_unverified_context = ssl._create_unverified_context()
else:
    # Not existing in Python 2.6
    ssl_unverified_context = None


def sanitize_url(url):
    """ Make sure this url works with urllib2 (ascii, http, etc) """
    if url and url.startswith("10."): # condition added to convert DOI to url
        url = u"http://doi.org/%s" % url
    elif url and not url.startswith("http"):
        url = u"http://%s" % url
    return url


def get_status_code(url):
    """ Perform HEAD request and return status code """
    try:
        request = requests.get(sanitize_url(url), headers = header)
        return request.status_code
    except requests.HTTPError as e:
        return "HTTP Error"
    except requests.URLRequired as e:
        return "URL Error"
    except requests.Timeout as e:
        return "Timeout Error"
    except requests.ConnectionError as e:
        return "Connection Error"
    except Exception as e:
        print(e, url)
        return None


def check_refs(refs, verbose=True, max_threads=MAX_THREADS_DEFAULT):
    """ Check if urls exist """
    codes = defaultdict(list)
    numberworking = 0 #counter for the number of working links

    def check_url(ref):
        url = ref.ref
        status_code = str(get_status_code(url))
        codes[status_code].append(ref)
        if verbose:
            if status_code.startswith("2") or status_code.startswith("3"): # added condition to make all 200 and 300 codes ok
                colorprint(OKGREEN, "%s - %s" % (status_code, url))
            else:
                colorprint(FAIL, "%s - %s" % (status_code, url))

    # Start a threadpool and add the check-url tasks
    try:
        pool = ThreadPool(5)
        pool.map(check_url, refs)
        pool.wait_completion()

    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        pass

    # Print summary
    print("\nSummary of link checker:")
    for c in sorted(codes):
        if c.startswith("2") or c.startswith("3"): # added condition to make all 200 and 300 codes count as being ok
            numberworking += len(codes[c])
        else:
            colorprint(FAIL, "%s broken (reason: %s)" % (len(codes[c]), c))
            for ref in codes[c]:
                o = u"  - %s" % ref.ref
                if ref.page > 0:
                    o += " (page %s)" % ref.page
                print(o)
    colorprint(OKGREEN, "%s working" % numberworking)


def download_urls(urls, output_directory, verbose=True,
                  max_threads=MAX_THREADS_DEFAULT):
    """ Download urls to a target directory """
    assert type(urls) in [list, tuple, set], "Urls must be some kind of list"
    assert len(urls), "Need urls"
    assert output_directory, "Need an output_directory"

    def vprint(s):
        if verbose:
            print(s)

    def download_url(url):
        try:
            fn = url.split("/")[-1]
            fn_download = os.path.join(output_directory, str(url))
            with open(fn_download, "wb") as f:
                request = requests.get(sanitize_url(url), headers = header)
                status_code = request.status_code
                if status_code == 200:
                    f.write(request.read())
                    colorprint(OKGREEN, "Downloaded '%s' to '%s'" %
                                        (url, fn_download))
                elif status_code == 302:
                    f.write(request.read())
                    colorprint(OKGREEN, "Downloaded '%s' to '%s'" %
                                        (url, fn_download))
                else:
                    colorprint(FAIL, "Error downloading '%s' (%s)" %
                                     (url, status_code))
        except requests.HTTPError as e:
            colorprint(FAIL, "Error downloading '%s' (%s)" % (url, e.code))
        except requests.URLRequired as e:
            colorprint(FAIL, "Error downloading '%s' (%s)" % (url, e.reason))
        except Exception as e:
            colorprint(FAIL, "Error downloading '%s' (%s)" % (url, str(e)))

    # Create directory
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        vprint("Created directory '%s'" % output_directory)

    try:
        pool = ThreadPool(5)
        pool.map(download_url, urls)
        pool.wait_completion()

    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        pass

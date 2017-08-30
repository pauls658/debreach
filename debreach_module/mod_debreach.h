#define debreachFilterName "DEBREACH"
#define DEBREACH_ARR_KEY "dbr"
#define DEBREACH_LEN_KEY "dblen"
#define DEBREACH_CAP_KEY "dbcap"

#include "util_filter.h"


int mod_debreach_taint_brs(request_rec *r, int start, int end);

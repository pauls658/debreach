PHP_ARG_ENABLE(debreach, whether to enable debreach
 support,
[ --enable-debreach Enable debreach support])

PHP_ARG_WITH(apxs2,,
[  --with-apxs2[=FILE]       Build shared Apache 2.0 Handler module. FILE is the optional
                          pathname to the Apache apxs tool [apxs]], no, no)

AC_MSG_CHECKING([for Apache 2.0 handler-module support via DSO through APXS])

if test "$PHP_DEBREACH" = "yes"; then
  if test "$PHP_APXS2" != "no"; then
    if test "$PHP_APXS2" = "yes"; then
      APXS=apxs
      $APXS -q CFLAGS >/dev/null 2>&1
      if test "$?" != "0" && test -x /usr/sbin/apxs; then
        APXS=/usr/sbin/apxs
      fi  
    else
      PHP_EXPAND_PATH($PHP_APXS2, APXS)
    fi  
  fi

  APXS_INCLUDEDIR=`$APXS -q INCLUDEDIR`
  APR_CONFIG=`$APXS -q APR_CONFIG 2>/dev/null ||
    echo $APR_BINDIR/apr-config`

  APR_INCLUDEDIR=`$APR_CONFIG --includedir`


  PHP_ADD_INCLUDE($APXS_INCLUDEDIR) 
  PHP_ADD_INCLUDE($APR_INCLUDEDIR) 
  
  AC_DEFINE(HAVE_DEBREACH, 1, [Whether you have debreach])
  PHP_NEW_EXTENSION(debreach, debreach.c, $ext_shared)
  dnl PHP_SELECT_SAPI(apache2handler, program, mod_php7.c sapi_apache2.c apache_config.c php_functions.c, $APACHE_CFLAGS)
fi

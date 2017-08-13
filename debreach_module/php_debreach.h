#ifndef PHP_DEBREACH_H
#define PHP_DEBREACH_H 1
#define PHP_DEBREACH_VERSION "1.0"
#define PHP_DEBREACH_EXTNAME "debreach"

PHP_FUNCTION(taint_brs);

extern zend_module_entry debreach_module_entry;
#define phpext_hello_ptr &debreach_module_entry

#endif

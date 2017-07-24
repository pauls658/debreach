mod_unknown.la: mod_unknown.slo
	$(SH_LINK) -rpath $(libexecdir) -module -avoid-version  mod_unknown.lo
DISTCLEAN_TARGETS = modules.mk
shared =  mod_unknown.la

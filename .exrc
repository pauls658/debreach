if &cp | set nocp | endif
map OF $
map OH ^ 
map QQQQ! :q!
map Q gq
let s:cpo_save=&cpo
set cpo&vim
nmap gx <Plug>NetrwBrowseX
nnoremap <silent> <Plug>NetrwBrowseX :call netrw#NetrwBrowseX(expand("<cWORD>"),0)
noremap <F4> +p:%j:%y+:sleep 2QQQQ!
map <F1> 
nnoremap <F9> :set invpaste paste?
noremap <F8> :set nonumber!
noremap <F7> :.,/^-- \n/-2dO
let &cpo=s:cpo_save
unlet s:cpo_save
set autowrite
set backspace=2
set cindent
set cinoptions=(0
set comments=sr:/*,mb:*,el:*/,://
set fileencodings=ucs-bom,utf-8,default,latin1
set formatoptions=croql
set helplang=en
set history=50
set ignorecase
set incsearch
set laststatus=2
set nomodeline
set pastetoggle=<F9>
set ruler
set runtimepath=~/.vim,/var/lib/vim/addons,/usr/share/vim/vimfiles,/usr/share/vim/vim74,/usr/share/vim/vimfiles/after,/var/lib/vim/addons/after,~/.vim/after
set shiftwidth=4
set showcmd
set showmatch
set smartcase
set spellfile=~/.vim/spell/en.utf-8.add
set statusline=%F%m%r%h%w\ (%l,%v)\ [%p%%\ of\ %LL,\ %{&ff}]
set suffixes=.bak,~,.swp,.o,.info,.aux,.log,.dvi,.bbl,.blg,.brf,.cb,.ind,.idx,.ilg,.inx,.out,.toc
set tabstop=4
set viminfo='20,\"1000
" vim: set ft=vim :

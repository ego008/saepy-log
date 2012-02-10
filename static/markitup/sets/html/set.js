// ----------------------------------------------------------------------------
// markItUp!
// ----------------------------------------------------------------------------
// Copyright (C) 2008 Jay Salvat
// http://markitup.jaysalvat.com/
// ----------------------------------------------------------------------------
myHtmlSettings = {
    nameSpace:       "html", // Useful to prevent multi-instances CSS conflict
    onShiftEnter:    {keepDefault:false, replaceWith:'<br />\n'},
    onCtrlEnter:     {keepDefault:false, openWith:'\n<p>', closeWith:'</p>\n'},
    onTab:           {keepDefault:false, openWith:'     '},
    markupSet:  [
        {name:'Heading 3', key:'3', openWith:'<h3(!( class="[![Class]!]")!)>', closeWith:'</h3> ', placeHolder:'Your title here...' },
        {name:'Heading 4', key:'4', openWith:'<h4(!( class="[![Class]!]")!)>', closeWith:'</h4> ', placeHolder:'Your title here...' },
        {name:'Heading 5', key:'5', openWith:'<h5(!( class="[![Class]!]")!)>', closeWith:'</h5> ', placeHolder:'Your title here...' },
        {separator:'---------------' },
        {name:'Bold', key:'B', openWith:'<strong>', closeWith:'</strong> ' },
        {name:'Italic', key:'I', openWith:'<em>', closeWith:'</em> '  },
        {name:'Stroke through', key:'S', openWith:'<del>', closeWith:'</del> ' },
        {name:'Colors', className:'colors', 
            dropMenu: [
            	{name:'Yellow',	openWith:'<span style="color:yellow">', 	closeWith:'</span> ', className:"col1-1" },
            	{name:'Orange',	openWith:'<span style="color:orange">', 	closeWith:'</span> ', className:"col1-2" },
            	{name:'Red', 	openWith:'<span style="color:red">', 	closeWith:'</span> ', className:"col1-3" },
            
            	{name:'Blue', 	openWith:'<span style="color:blue">', 	closeWith:'</span> ', className:"col2-1" },
            	{name:'Purple', openWith:'<span style="color:purple">', 	closeWith:'</span> ', className:"col2-2" },
            	{name:'Green', 	openWith:'<span style="color:green">', 	closeWith:'</span> ', className:"col2-3" },
            
            	{name:'White', 	openWith:'<span style="color:white">', 	closeWith:'</span> ', className:"col3-1" },
            	{name:'Gray', 	openWith:'<span style="color:gray">', 	closeWith:'</span> ', className:"col3-2" },
            	{name:'Black',	openWith:'<span style="color:black">', 	closeWith:'</span> ', className:"col3-3" }
            ]        	
        },        
        {separator:'---------------' },
        {name:'Ul', openWith:'<ul>\n', closeWith:'</ul>\n' },
        {name:'Ol', openWith:'<ol>\n', closeWith:'</ol>\n' },
        {name:'Li', openWith:'<li>', closeWith:'</li> ' },
        {separator:'---------------' },
        {name:'Picture', key:'P', replaceWith:'<img src="[![Source:!:http://]!]" alt="[![Alternative text]!]" /> ' },
        {name:'Link', key:'L', openWith:'<a href="[![Link:!:http://]!]"(!( title="[![Title]!]")!) target="_blank">', closeWith:'</a> ', placeHolder:'Your text to link...' },
        {separator:'---------------' },
        {name:'Quotes', openWith:'<blockquote>', closeWith:'</blockquote> '},
        {name:'Code', openWith:'[code]', closeWith:'[/code]'},        
        {name:'Clean', replaceWith:function(h) { return h.selection.replace(/<(.*?)>/g, "") } },
        {name:'Cut', openWith:'\n <!--more--> \n', closeWith:'' }
    ]
}
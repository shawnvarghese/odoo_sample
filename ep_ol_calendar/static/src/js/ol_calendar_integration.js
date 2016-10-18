openerp.ep_ol_calendar=function(instance)
{
    var _t = instance.web._t,
    _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web_calendar.CalendarView.include(
	{		
        view_loading: function(r)
        {
            var self = this;
            this.$el.on('click', 'button.ol_sync', function()
    		{
                self.ol_sync_calendar(r);
            });

            return this._super(r);
        },
        ol_sync_calendar: function(res, button) 
        {
            var self = this;
            var context = instance.web.pyeval.eval('context');

            self.rpc('/ep_ol_calendar/sync',{
            	arch: res.arch,
                fields: res.fields,
                model: res.model,
                fromurl: window.location.href,
                local_context: context
            }).done(function(o)
            		{
            			instance.web.redirect(o.url);
            		});
        },        
	});
    
    
    instance.web_calendar.CalendarView.include(
	{
	    extraSideBar: function()
	    {
	        this._super();
	        if (this.dataset.model == "calendar.event")
	        {
	            this.$el.find('.oe_calendar_filter').prepend(QWeb.render('outlook_sync'));
	        }
	    },
	});
}
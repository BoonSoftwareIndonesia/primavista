odoo.define('api_ven.CheckinButton', function(require){
    'use strict';
    
    console.log('Checkin Widget Started');
//     var FormController = require('web.FormController')
    
    var core = require('web.core');
    var QWeb = core.qweb;
    var Widget = require('web.Widget');
    var widgetRegistry = require('web.widget_registry')
    
    var Checkin = Widget.extend({
        eventId: -1,
        template: 'CheckinButton',
        events: {
            "click .checkin_button":'getChecked',
        },
        init: function (parent) {
            this._super(parent);
        },
        getChecked:function(){
            console.log('Clicked!');
            this.do_notify(_t("Success"), _t("Your signature request has been sent."));
        },
    });
    
//     var AbstractField = require('web.AbstractField');
//     var FieldRegistry = require('web.field_registry');
    
//     var Checkin = AbstractField.extend({
//         eventId: -1,
//         template: 'CheckinButton',
//         events: {
//             'click .checkin_button': 'getChecked',
//         },
//         init: function () {
//             this._super.apply(this, arguments);
//             if(this.nodeOptions.eventId){
//               this.eventId = this.nodeOptions.eventId;  
//             }
//         },
//         getChecked: function () {
//             alert('clieked');
//             console.log('Clicked!');
//         },
//     });
    
    widgetRegistry.add(
        'CheckinButton', Checkin
    );
    
    return Checkin;
});
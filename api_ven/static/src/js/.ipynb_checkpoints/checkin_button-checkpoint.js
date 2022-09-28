odoo.define('api_ven.CheckinButton', function(require){
    'use strict';
    
    console.log('Checkin Widget Started');
//     var FormController = require('web.FormController')
    
    var core = require('web.core');
    var QWeb = core.qweb;
    var Widget = require('web.Widget');
    var widgetRegistry = require('web.widget_registry')
    
    var Checkin = Widget.extend({
        calendarId: -1,
        template: 'CheckinButton',
        init: function (parent) {
            this._super(parent);
        },
    });
    
    
    $(document).on('click', '.checkin_button.o_widget', function(){
         navigator.geolocation.getCurrentPosition(function(position){
            let dist = getDistance(position.coords.longitude, position.coords.latitude);
            console.log(dist);
                    
        });
     });
    
    function getDistance(longitude, latitude){
        const R = 6371; //Radius of earth in KM

        const latTarget = -6.191048862358757;
        const longTarget = 106.76797591217014;

        let x1 = latTarget - latitude;
        let dLat = x1.toRad();
        let x2 = longTarget - longitude;
        let dLong = x2.toRad();

        let a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(latitude.toRad()) * Math.cos(latTarget.toRad()) * Math.sin(dLong/2) * Math.sin(dLong/2);

        let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        let d = R * c;

        return d;
    }
    
    Number.prototype.toRad = function() {
        return this * Math.PI / 180;
    } 
    
    widgetRegistry.add(
        'CheckinButton', Checkin
    );
    
    return Checkin;
});
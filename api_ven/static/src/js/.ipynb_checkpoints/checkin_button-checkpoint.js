odoo.define('api_ven.CheckinButton', function(require){
    'use strict';
    
    console.log('Checkin Widget Started');
//     var FormController = require('web.FormController')
    
    var core = require('web.core');
    var QWeb = core.qweb;
    var Widget = require('web.Widget');
    var widgetRegistry = require('web.widget_registry');
    var rpc = require('web.rpc');
    
    
    var Checkin = Widget.extend({
        calendarId: -1,
        selector: ".checkin_button.o_widget",
        template: 'CheckinButton',
        model: "calendar.event",
        events: {
            'click': '_onClick',
        },
        init: function (parent) {
            this._super(parent);
        },
        _onClick: function(){
            var self = this;
            let dist;
            
            navigator.geolocation.getCurrentPosition(function(position){
                let id = getParsedUrl(window.location.href);
                console.log(id);

                let locLat = $("td > span[name='x_studio_latitude']").text();
                let locLong = $("td > span[name='x_studio_longitude']").text();

                dist = getDistance(position.coords.longitude, position.coords.latitude, locLong, locLat);
                console.log("From on click " + dist);
                let notifString ="You are currently " + dist + " km away from the meeting location";
                
                let res = rpc.query({
                    model: self.model,
                    method: 'action_test'
                }).then(function(result){
                    console.log("Result rpc " + result);
                    self.do_action(result);
                }).catch(function(err){
                    console.log(err);
                });

                console.log('With model: '+ self.model);
            });
        }
    });
    
//     From JQuerry
//     $(document).on('click', '.checkin_button.o_widget', function(){
//         navigator.geolocation.getCurrentPosition(function(position){
//             let id = getParsedUrl(window.location.href);
//             console.log(id);

//             let locLat = $("td > span[name='x_studio_latitude']").text();
//             let locLong = $("td > span[name='x_studio_longitude']").text();
            
//             let dist = getDistance(position.coords.longitude, position.coords.latitude, locLong, locLat);
//             console.log(dist);
//             let notifString ="You are currently " + dist + " km away from the meeting location"
            
//             this._rpc({
//                 model: 'calendar.event',
//                 method: 'action_test',
//                 args: [id],
//             }).then(function (result) {
//                 this.do_action(result);
//             });
//         });
//      });
    
    function getParsedUrl(url){
        let result = "";
        let indexIdStart = url.indexOf('#id='); //Getting the '#' index
        let indexIdEnd = url.indexOf('&'); //Getting index '&' in '#id=9&'
        indexIdStart += 4; //Getting index after '='
        result = url.slice(indexIdStart, indexIdEnd);
        
        return result
    }
    
    function getDistance(longitude, latitude, longEvent, latEvent){
        const R = 6371; //Radius of earth in KM

        const longTarget = Number(parseFloat(longEvent));
        const latTarget = Number(parseFloat(latEvent));
            
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
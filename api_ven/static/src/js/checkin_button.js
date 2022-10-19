odoo.define('api_ven.CheckinButton', function(require){
    'use strict';
    
    console.log('Checkin Widget Started');
    
    var core = require('web.core');
    var QWeb = core.qweb;
    var Widget = require('web.Widget');
    var widgetRegistry = require('web.widget_registry');
    var rpc = require('web.rpc');
    
    var Checkin = Widget.extend({
        selector: "#checkin_btn",
        template: 'CheckinButton',
        model: "calendar.event",
        events: {
            'click': '_onClick',
        },
        eventId: -1,
        init: function () {
//          What happens when the widget is first initialized
            var self = this;
            this._super.apply(this, arguments);
            
            // Set Timeout because from meeting -> calendar event, the link fetched would still be the meeting menu's url, not the calendar event's
            setTimeout(function() {
                console.log(window.location.href);
                self.eventId = self._getParsedUrl(window.location.href);
                console.log("Init with id: " + self.eventId);
            }, 1000);
            
//             console.log('Updated');
        },
//         _render: function(){
//             var self = this;
//             let res = rpc.query({
//                 model: self.model,
//                 method: 'get_check_status',
//                 args:[("eventId", '=',self.eventId)]
//             }).then(function(result){
//                 console.log("Result rpc: " + result);
                
// //                 Still not working, span not selected
//                 console.log(document.getElementById('checkin_text').innerHTML);

//                 if(result && !(self.$('span#checkin_text').hasClass('text-warning'))){
//                     self.$('#checkin_btn > span#checkin_text').addClass('text-warning');
//                 }
//             }).catch(function(err){
//                 console.log(err);
//             });
//         },
        _onClick: function(){
//             var self = this to make sure the self refers to the record, not the navigator
            var self = this;
            let dist;

//          Check if event ID is really set
            if(self.eventId == -1){
                self.eventId = self._getParsedUrl(window.location.href);
                console.log("Event ID changed to: " + self.eventId)
            }
            
//             navigator for user's location, jQuery to get calendar event's lat long loc
            navigator.geolocation.getCurrentPosition(function(position){
                // Get lat long via jquery
                let locLat = $("td > span[name='x_studio_latitude']").text();
                let locLong = $("td > span[name='x_studio_longitude']").text();
                let loc = $("td > span[name='location']").text();

                if(loc == 'Online'){
                    //Online
//                    Check event as True, show notification, reload window to update the render
                    console.log('Online');
                    self._checkingEvent();
                    self._showNotification('Success', 'Online checkin success!');
                    window.location.reload();
                    return;
                }
                
                if(loc == ""){
                    //None
//                     No need to reload, nothing to be rendered again
                    console.log('No location');
                    //Show notification no location
                    self._showNotification('Failed', 'No location is attached to the calendar event. Please edit and fill in the location.');
                    return;
                }
                
//                 Calculate distance using Haversine formula
                dist = self._getDistance(position.coords.longitude, position.coords.latitude, locLong, locLat);
                console.log("From on click " + dist);
                let notifString ="You are currently " + dist + " km away from the meeting location";
                
                //Check distance threshold
                if(dist < 1){
                    console.log('Checked in');
                    //Change checkin_status attribute to 1
                    self._checkingEvent();
                    self._showNotification('Success','Checkin success!');
                    window.location.reload();
                    return;
                }
                
                self._showNotification('Failed','You are too far away from the meeting location');
            });
        },
        _showNotification: function(notifTitle, notifMsg){
//             Using rpc to call method from model
            var self = this;
            let res = rpc.query({
                model: self.model,
                method: 'send_notification',
                args: [[notifTitle, notifMsg]]
            }).then(function(result){
                console.log("Result rpc " + result);
                self.do_action(result);
            }).catch(function(err){
                console.log(err);
            });
        },
        _checkingEvent: function(){
            var self = this;

            let res = rpc.query({
                model: self.model,
                method: 'checking_in',
                args:[("eventId", '=',self.eventId)]
            }).then(function(result){
                console.log("Result rpc: " + result);
            }).catch(function(err){
                console.log(err);
            });
        },
        _getParsedUrl: function(url){
//          Getting calendar event's id from url
            let result = "";
            let indexIdStart = url.indexOf('#id='); //Getting the '#' index
            
            if (indexIdStart == -1){
                return -1;
            }
            
            let indexIdEnd = url.indexOf('&'); //Getting index '&' in '#id=9&'
            indexIdStart += 4; //Getting index after '='
            result = url.slice(indexIdStart, indexIdEnd);

            return result
        },
        _getDistance: function(longitude, latitude, longEvent, latEvent){
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
    
    Number.prototype.toRad = function() {
        return this * Math.PI / 180;
    } 
    
//     Register the widget in odoo System
    widgetRegistry.add(
        'CheckinButton', Checkin
    );
    
    return Checkin;
});

//The widget's UI is in api_ven/static/src/xml. We put it in odoo's module by calling it in in api_ven/views/. The widget's logic is in this file. And the method called from rpc is in the model.
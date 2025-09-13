---------------------
Exotel
---------------------

.. currentmodule:: exotelpy.exotel

.. IMPORTANT::
   Please refer to linked `Exotel API docs <https://developer.exotel.com/api/sms>`_ for more details

.. autoclass:: Exotel


   .. rubric:: Campaigns

   .. automethod:: create_campaign
   .. automethod:: create_campaign_with_list
   .. automethod:: get_campaign_details
   .. automethod:: delete_campaign
   .. automethod:: get_campaign_call_details
   .. automethod:: get_bulk_campaign_details


   .. rubric:: Contacts
   .. automethod:: create_contacts
   .. automethod:: get_contact_details
   .. automethod:: delete_contact
   .. automethod:: delete_contacts
   

   .. rubric:: Lists
   .. automethod:: create_list
   .. automethod:: add_contacts_to_list
   .. automethod:: delete_list
   .. automethod:: get_list_details
   .. automethod:: get_bulk_lists
   .. automethod:: get_list_contacts


   .. rubric:: SMS Campaigns
   .. DANGER::
      SMS Campaign Methods will be soon deprecated as Exotel has deprecated the endpoint
   .. automethod:: create_sms_campaign
   .. automethod:: create_sms_campaign_with_list
   .. automethod:: create_message_campaign
   .. automethod:: create_message_campaign_with_list
   .. automethod:: get_sms_campaign_details
   .. automethod:: get_bulk_sms_campaign_details
   .. automethod:: get_sms_campaign_sms_details


   .. rubric:: SMS
   .. automethod:: get_sms_details
   .. automethod:: send_bulk_sms

   .. rubric:: Exophones
   .. automethod:: get_all_exophones
   .. automethod:: get_exophone_details
   .. automethod:: get_exophone_heartbeat

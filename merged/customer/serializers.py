from rest_framework import serializers
from .models import Customer, CustomerMobile, CustomerAddress, MoreAddress

class CustomerMobileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerMobile
        fields = ['id', 'mobile']

class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id', 'address', 'pincode', 'city', 'state', 'country']

class MoreAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoreAddress
        fields = ['id', 'name', 'mobile', 'email', 'address', 'pincode', 'city', 'state', 'country']

class CustomerSerializer(serializers.ModelSerializer):
    mobiles = CustomerMobileSerializer(many=True, read_only=True)
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    more_addresses = MoreAddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'mobiles', 'addresses', 'more_addresses']
        read_only_fields = ['id']

class CustomerUpdateSerializer(serializers.ModelSerializer):
    mobiles = CustomerMobileSerializer(many=True, required=False)
    addresses = CustomerAddressSerializer(many=True, required=False)
    more_addresses = MoreAddressSerializer(many=True, required=False)
    
    class Meta:
        model = Customer
        fields = ['name', 'email', 'mobiles', 'addresses', 'more_addresses']

    def update(self, instance, validated_data):
        # Update customer basic info
        instance.name = validated_data.get('name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        # Update mobiles
        if 'mobiles' in validated_data:
            # Delete existing mobiles
            instance.mobiles.all().delete()
            # Create new mobiles
            for mobile_data in validated_data['mobiles']:
                CustomerMobile.objects.create(customer=instance, **mobile_data)

        # Update addresses
        if 'addresses' in validated_data:
            # Delete existing addresses
            instance.addresses.all().delete()
            # Create new addresses
            for address_data in validated_data['addresses']:
                CustomerAddress.objects.create(customer=instance, **address_data)

        # Update more addresses
        if 'more_addresses' in validated_data:
            # Delete existing more addresses
            instance.more_addresses.all().delete()
            # Create new more addresses
            for more_address_data in validated_data['more_addresses']:
                MoreAddress.objects.create(customer=instance, **more_address_data)

        return instance 